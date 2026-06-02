from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .mcp_runtime import MCPToolResult, call_mcp_tool


@dataclass(slots=True)
class DAGStep:
    step_id: str
    tool: str
    parameters: dict[str, Any] = field(default_factory=dict)
    depends_on: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "tool": self.tool,
            "parameters": self.parameters,
            "depends_on": self.depends_on,
        }


@dataclass(slots=True)
class DAGExecutionPlan:
    name: str
    steps: list[DAGStep]


@dataclass(slots=True)
class DAGStepResult:
    step_id: str
    tool: str
    success: bool
    payload: dict[str, Any]
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "tool": self.tool,
            "success": self.success,
            "payload": self.payload,
            "error": self.error,
        }


@dataclass(slots=True)
class DAGRunResult:
    name: str
    status: str
    steps: list[DAGStepResult]

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "steps": [step.to_dict() for step in self.steps],
        }


def _topological_order(steps: list[DAGStep]) -> list[DAGStep]:
    by_id = {step.step_id: step for step in steps}
    missing = {
        dependency
        for step in steps
        for dependency in step.depends_on
        if dependency not in by_id
    }
    if missing:
        raise ValueError(f"DAG contains missing dependencies: {', '.join(sorted(missing))}")

    ordered: list[DAGStep] = []
    temporary: set[str] = set()
    permanent: set[str] = set()

    def visit(step: DAGStep) -> None:
        if step.step_id in permanent:
            return
        if step.step_id in temporary:
            raise ValueError(f"DAG contains a cycle at step: {step.step_id}")
        temporary.add(step.step_id)
        for dependency in step.depends_on:
            visit(by_id[dependency])
        temporary.remove(step.step_id)
        permanent.add(step.step_id)
        ordered.append(step)

    for step in steps:
        visit(step)
    return ordered


def run_dag_plan(plan: DAGExecutionPlan) -> DAGRunResult:
    results: list[DAGStepResult] = []
    for step in _topological_order(plan.steps):
        tool_result: MCPToolResult = call_mcp_tool(step.tool, step.parameters)
        result = DAGStepResult(
            step_id=step.step_id,
            tool=step.tool,
            success=tool_result.success,
            payload=tool_result.payload,
            error=tool_result.error,
        )
        results.append(result)
        if not result.success:
            return DAGRunResult(name=plan.name, status="failed", steps=results)
    return DAGRunResult(name=plan.name, status="succeeded", steps=results)
