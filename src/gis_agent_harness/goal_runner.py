from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .agent_loop import AgentLoop, AgentRunResult, AgentTask
from .config import HarnessConfig
from .execution_plan import ExecutionPlan, load_execution_plan
from .llm_adapters import build_llm_adapter
from .llm_router import LLMRouter
from .state_hooks import StateHook
from .state_store import StateStore
from .task_templates import TemplateRegistry
from .telemetry import TelemetryWriter


@dataclass(slots=True)
class GoalSpec:
    template_id: str | None
    inputs: dict[str, Any] = field(default_factory=dict)
    task_summary: str | None = None
    max_iterations: int | None = None
    use_mock: bool | None = None
    run_root: Path | None = None
    state_file: Path | None = None
    plan_file: Path | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["run_root"] = str(self.run_root) if self.run_root else None
        payload["state_file"] = str(self.state_file) if self.state_file else None
        payload["plan_file"] = str(self.plan_file) if self.plan_file else None
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

    def _load_plan(self, spec: GoalSpec) -> ExecutionPlan | None:
        if spec.plan_file is None:
            return None
        return load_execution_plan(spec.plan_file)

    def _runtime_config(self, spec: GoalSpec, *, plan: ExecutionPlan | None = None) -> HarnessConfig:
        runtime = self.config.copy()
        if spec.use_mock is not None:
            runtime.use_mock = spec.use_mock
            if spec.use_mock and runtime.provider != "mock":
                runtime.provider = "mock"
        if spec.max_iterations is not None:
            runtime.max_iterations = spec.max_iterations
        elif plan is not None and plan.constraints.max_iterations is not None:
            runtime.max_iterations = plan.constraints.max_iterations
        if spec.run_root is not None:
            runtime.run_root = spec.run_root
        if spec.state_file is not None:
            runtime.state_file = spec.state_file
        if str(runtime.sandbox_write_root).startswith(str(self.config.run_root)):
            runtime.sandbox_write_root = runtime.run_root / "artifacts"
        if str(runtime.telemetry_file).startswith(str(self.config.run_root)):
            runtime.telemetry_file = runtime.run_root / "telemetry.jsonl"
        return runtime

    def _resolve_template_id(self, spec: GoalSpec, *, plan: ExecutionPlan | None) -> str:
        template_id = spec.template_id or (plan.template_id if plan is not None else None)
        if template_id:
            return template_id
        raise ValueError("A template id is required via GoalSpec.template_id or the execution plan file.")

    def _merged_inputs(self, spec: GoalSpec, *, plan: ExecutionPlan | None) -> dict[str, Any]:
        inputs = dict(plan.inputs) if plan is not None else {}
        inputs.update(spec.inputs)
        if plan is not None and plan.constraints.source_crs and not inputs.get("source_crs"):
            inputs["source_crs"] = plan.constraints.source_crs
        return inputs

    def build_task(self, spec: GoalSpec) -> AgentTask:
        plan = self._load_plan(spec)
        runtime = self._runtime_config(spec, plan=plan)
        task = self.registry.render_task(
            self._resolve_template_id(spec, plan=plan),
            values=self._merged_inputs(spec, plan=plan),
            max_iterations=spec.max_iterations or runtime.max_iterations,
            task_summary=spec.task_summary or (plan.task_summary if plan is not None else None),
        )
        if plan is not None:
            task.allowed_actions = list(plan.constraints.allowed_actions)
            task.target_crs = plan.constraints.target_crs
            task.workspace_root = plan.constraints.workspace_root
            task.plan_name = plan.name
            task.plan_path = str(plan.path)
            if not task.source_crs and plan.constraints.source_crs:
                task.source_crs = plan.constraints.source_crs
        return task

    def preview(self, spec: GoalSpec) -> dict[str, Any]:
        plan = self._load_plan(spec)
        template = self.registry.get(self._resolve_template_id(spec, plan=plan))
        task = self.build_task(spec)
        return {
            "template": template.to_dict(),
            "spec": spec.to_dict(),
            "task": task.to_dict(),
            "plan": plan.to_dict() if plan is not None else None,
        }

    def run(self, spec: GoalSpec, *, extra_hooks: list[StateHook] | None = None) -> AgentRunResult:
        plan = self._load_plan(spec)
        runtime = self._runtime_config(spec, plan=plan)
        task = self.build_task(spec)
        return run_agent_task(task, runtime, extra_hooks=extra_hooks)
