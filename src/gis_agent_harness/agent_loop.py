from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .config import HarnessConfig
from .errors import Observation
from .guardrails import preflight_dataset_checks
from .llm_router import AgentDecision, LLMRouter
from .logging_utils import new_run_id
from .sandbox import SandboxRunner
from .state_store import StateSnapshot, StateStore


@dataclass(slots=True)
class AgentTask:
    task_summary: str
    vector_path: str
    raster_path: str | None = None
    source_crs: str | None = None
    max_iterations: int = 3

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class AgentRunResult:
    status: str
    run_id: str
    iterations: int
    final_vector_path: str
    summary: str
    observations: list[Observation] = field(default_factory=list)
    decisions: list[AgentDecision] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "run_id": self.run_id,
            "iterations": self.iterations,
            "final_vector_path": self.final_vector_path,
            "summary": self.summary,
            "observations": [item.to_dict() for item in self.observations],
            "decisions": [item.to_dict() for item in self.decisions],
        }


class AgentLoop:
    def __init__(
        self,
        *,
        config: HarnessConfig,
        router: LLMRouter,
        sandbox: SandboxRunner | None = None,
        state_store: StateStore | None = None,
    ) -> None:
        self.config = config
        self.router = router
        self.sandbox = sandbox or SandboxRunner(config.run_root, timeout_seconds=config.timeout_seconds)
        self.state_store = state_store or StateStore(config.state_file, config.run_root)

    def run(self, task: AgentTask) -> AgentRunResult:
        run_id = new_run_id("gis")
        current_vector_path = Path(task.vector_path)
        repeated_fingerprints: set[str] = set()
        decision_history: list[AgentDecision] = []
        carry_observations: list[Observation] | None = None

        self.state_store.append(
            StateSnapshot(
                run_id=run_id,
                iteration=0,
                stage="start",
                status="running",
                summary=task.task_summary,
                artifacts={"task": task.to_dict()},
            )
        )

        for iteration in range(1, task.max_iterations + 1):
            observations = carry_observations or preflight_dataset_checks(
                current_vector_path,
                task.raster_path,
            )
            carry_observations = None

            if not observations:
                summary = f"Task succeeded after {iteration - 1} repair step(s)."
                self.state_store.append(
                    StateSnapshot(
                        run_id=run_id,
                        iteration=iteration,
                        stage="complete",
                        status="succeeded",
                        summary=summary,
                        artifacts={"final_vector_path": str(current_vector_path)},
                    )
                )
                return AgentRunResult(
                    status="succeeded",
                    run_id=run_id,
                    iterations=iteration - 1,
                    final_vector_path=str(current_vector_path),
                    summary=summary,
                    decisions=decision_history,
                )

            fingerprint = "|".join(sorted(item.fingerprint() for item in observations))
            self.state_store.append(
                StateSnapshot(
                    run_id=run_id,
                    iteration=iteration,
                    stage="observe",
                    status="blocked",
                    summary="Preflight checks found issues.",
                    observations=observations,
                    artifacts={"current_vector_path": str(current_vector_path)},
                )
            )
            if fingerprint in repeated_fingerprints:
                summary = "Agent loop stopped because the same observation fingerprint repeated."
                self.state_store.append(
                    StateSnapshot(
                        run_id=run_id,
                        iteration=iteration,
                        stage="stop",
                        status="failed",
                        summary=summary,
                        observations=observations,
                        artifacts={"current_vector_path": str(current_vector_path)},
                    )
                )
                return AgentRunResult(
                    status="failed",
                    run_id=run_id,
                    iterations=iteration,
                    final_vector_path=str(current_vector_path),
                    summary=summary,
                    observations=observations,
                    decisions=decision_history,
                )
            repeated_fingerprints.add(fingerprint)

            decision = self.router.plan_repair(
                task_summary=task.task_summary,
                observations=observations,
                current_vector_path=current_vector_path,
                raster_path=task.raster_path,
                run_root=self.config.run_root,
                run_id=run_id,
                iteration=iteration,
                source_crs=task.source_crs,
            )
            decision_history.append(decision)
            self.state_store.append(
                StateSnapshot(
                    run_id=run_id,
                    iteration=iteration,
                    stage="thought",
                    status="planned",
                    summary=decision.summary,
                    observations=observations,
                    artifacts={
                        "action": decision.action,
                        "model_used": decision.model_used,
                        "fallback_used": decision.fallback_used,
                        "output_vector_path": decision.output_vector_path,
                    },
                )
            )

            sandbox_result = self.sandbox.run_python(
                decision.script,
                run_id=run_id,
                step_name=f"iter-{iteration}",
            )
            action_status = "succeeded" if sandbox_result.success else "failed"
            self.state_store.append(
                StateSnapshot(
                    run_id=run_id,
                    iteration=iteration,
                    stage="action",
                    status=action_status,
                    summary=f"Executed {decision.action} repair script.",
                    observations=sandbox_result.observations,
                    artifacts={
                        "script_path": sandbox_result.script_path,
                        "returncode": sandbox_result.returncode,
                        "timed_out": sandbox_result.timed_out,
                    },
                )
            )

            if sandbox_result.success and decision.output_vector_path:
                current_vector_path = Path(decision.output_vector_path)
                continue

            carry_observations = [sandbox_result.to_observation()]

        summary = "Agent loop reached the maximum iteration limit."
        final_observations = carry_observations or preflight_dataset_checks(current_vector_path, task.raster_path)
        self.state_store.append(
            StateSnapshot(
                run_id=run_id,
                iteration=task.max_iterations,
                stage="stop",
                status="failed",
                summary=summary,
                observations=final_observations,
                artifacts={"current_vector_path": str(current_vector_path)},
            )
        )
        return AgentRunResult(
            status="failed",
            run_id=run_id,
            iterations=task.max_iterations,
            final_vector_path=str(current_vector_path),
            summary=summary,
            observations=final_observations,
            decisions=decision_history,
        )
