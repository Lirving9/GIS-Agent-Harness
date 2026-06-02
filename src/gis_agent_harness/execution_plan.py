from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass(slots=True)
class PlanConstraints:
    max_iterations: int | None = None
    source_crs: str | None = None
    target_crs: str | None = None
    workspace_root: str | None = None
    allowed_actions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class PlanStep:
    step_id: str
    objective: str
    notes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.step_id,
            "objective": self.objective,
            "notes": self.notes,
        }


@dataclass(slots=True)
class ExecutionPlan:
    path: Path
    name: str
    template_id: str | None = None
    task_summary: str | None = None
    description: str | None = None
    inputs: dict[str, Any] = field(default_factory=dict)
    constraints: PlanConstraints = field(default_factory=PlanConstraints)
    steps: list[PlanStep] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": str(self.path),
            "name": self.name,
            "template_id": self.template_id,
            "task_summary": self.task_summary,
            "description": self.description,
            "inputs": dict(self.inputs),
            "constraints": self.constraints.to_dict(),
            "steps": [step.to_dict() for step in self.steps],
        }


def load_execution_plan(path: str | Path) -> ExecutionPlan:
    plan_path = Path(path)
    if not plan_path.exists():
        raise FileNotFoundError(f"Execution plan does not exist: {plan_path}")

    payload = _load_payload(plan_path)
    if not isinstance(payload, dict):
        raise ValueError(f"Execution plan must deserialize to a mapping: {plan_path}")

    constraints_payload = payload.get("constraints") or {}
    if not isinstance(constraints_payload, dict):
        raise ValueError("Execution plan constraints must be a mapping.")

    steps: list[PlanStep] = []
    for item in payload.get("steps") or []:
        if not isinstance(item, dict):
            raise ValueError("Execution plan steps must be mappings.")
        step_id = str(item.get("id") or item.get("step_id") or "").strip()
        objective = str(item.get("objective") or "").strip()
        if not step_id or not objective:
            raise ValueError("Execution plan steps require both id and objective.")
        steps.append(
            PlanStep(
                step_id=step_id,
                objective=objective,
                notes=str(item.get("notes")).strip() if item.get("notes") else None,
            )
        )

    return ExecutionPlan(
        path=plan_path,
        name=str(payload.get("name") or payload.get("title") or plan_path.stem),
        template_id=str(payload["template_id"]) if payload.get("template_id") else None,
        task_summary=str(payload["task_summary"]) if payload.get("task_summary") else None,
        description=str(payload["description"]) if payload.get("description") else None,
        inputs=dict(payload.get("inputs") or {}),
        constraints=PlanConstraints(
            max_iterations=(
                int(constraints_payload["max_iterations"])
                if constraints_payload.get("max_iterations") is not None
                else None
            ),
            source_crs=(
                str(constraints_payload["source_crs"]) if constraints_payload.get("source_crs") else None
            ),
            target_crs=(
                str(constraints_payload["target_crs"]) if constraints_payload.get("target_crs") else None
            ),
            workspace_root=(
                str(constraints_payload["workspace_root"])
                if constraints_payload.get("workspace_root")
                else None
            ),
            allowed_actions=[str(item) for item in constraints_payload.get("allowed_actions") or []],
        ),
        steps=steps,
    )


def _load_payload(path: Path) -> dict[str, Any]:
    suffix = path.suffix.lower()
    text = path.read_text(encoding="utf-8")
    if suffix in {".yaml", ".yml"}:
        return yaml.safe_load(text) or {}
    if suffix == ".md":
        frontmatter = _extract_markdown_frontmatter(text)
        if frontmatter is None:
            raise ValueError(f"Markdown plan must start with YAML frontmatter: {path}")
        return yaml.safe_load(frontmatter) or {}
    raise ValueError(f"Unsupported execution plan format: {path}")


def _extract_markdown_frontmatter(text: str) -> str | None:
    if not text.startswith("---\n"):
        return None
    _, _, remainder = text.partition("---\n")
    frontmatter, separator, _ = remainder.partition("\n---")
    return frontmatter if separator else None
