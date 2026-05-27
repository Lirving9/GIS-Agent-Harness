from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .agent_loop import AgentLoop, AgentRunResult, AgentTask
from .config import HarnessConfig
from .llm_adapters import build_llm_adapter
from .llm_router import LLMRouter
from .state_hooks import StateHook
from .state_store import StateStore
from .task_templates import TemplateRegistry
from .telemetry import TelemetryWriter


@dataclass(slots=True)
class GoalSpec:
    template_id: str
    inputs: dict[str, Any] = field(default_factory=dict)
    task_summary: str | None = None
    max_iterations: int | None = None
    use_mock: bool | None = None
    run_root: Path | None = None
    state_file: Path | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["run_root"] = str(self.run_root) if self.run_root else None
        payload["state_file"] = str(self.state_file) if self.state_file else None
        return payload


def build_state_store(config: HarnessConfig, *, extra_hooks: list[StateHook] | None = None) -> StateStore:
    hooks: list[StateHook] = []
    if config.telemetry_local_only:
        hooks.append(TelemetryWriter(config.telemetry_file))
    hooks.extend(extra_hooks or [])
    return StateStore(config.state_file, config.run_root, hooks=hooks)


def build_router(config: HarnessConfig) -> LLMRouter:
    return LLMRouter(
        primary_model=config.primary_model,
        fallback_model=config.fallback_model,
        api_base=config.api_base,
        api_key=config.api_key,
        reasoning_effort=config.reasoning_effort,
        client=build_llm_adapter(config),
        use_mock=config.use_mock,
        litellm_config_path=str(config.litellm_config_path),
    )


def run_agent_task(
    task: AgentTask,
    config: HarnessConfig,
    *,
    extra_hooks: list[StateHook] | None = None,
) -> AgentRunResult:
    loop = AgentLoop(
        config=config,
        router=build_router(config),
        state_store=build_state_store(config, extra_hooks=extra_hooks),
    )
    return loop.run(task)


class GoalRunner:
    def __init__(
        self,
        config: HarnessConfig,
        *,
        registry: TemplateRegistry | None = None,
    ) -> None:
        self.config = config
        self.registry = registry or TemplateRegistry()

    def _runtime_config(self, spec: GoalSpec) -> HarnessConfig:
        runtime = self.config.copy()
        if spec.use_mock is not None:
            runtime.use_mock = spec.use_mock
            if spec.use_mock and runtime.provider != "mock":
                runtime.provider = "mock"
        if spec.max_iterations is not None:
            runtime.max_iterations = spec.max_iterations
        if spec.run_root is not None:
            runtime.run_root = spec.run_root
        if spec.state_file is not None:
            runtime.state_file = spec.state_file
        if str(runtime.sandbox_write_root).startswith(str(self.config.run_root)):
            runtime.sandbox_write_root = runtime.run_root / "artifacts"
        if str(runtime.telemetry_file).startswith(str(self.config.run_root)):
            runtime.telemetry_file = runtime.run_root / "telemetry.jsonl"
        return runtime

    def build_task(self, spec: GoalSpec) -> AgentTask:
        runtime = self._runtime_config(spec)
        return self.registry.render_task(
            spec.template_id,
            values=spec.inputs,
            max_iterations=spec.max_iterations or runtime.max_iterations,
            task_summary=spec.task_summary,
        )

    def preview(self, spec: GoalSpec) -> dict[str, Any]:
        template = self.registry.get(spec.template_id)
        task = self.build_task(spec)
        return {
            "template": template.to_dict(),
            "spec": spec.to_dict(),
            "task": task.to_dict(),
        }

    def run(self, spec: GoalSpec, *, extra_hooks: list[StateHook] | None = None) -> AgentRunResult:
        runtime = self._runtime_config(spec)
        task = self.build_task(spec)
        return run_agent_task(task, runtime, extra_hooks=extra_hooks)
