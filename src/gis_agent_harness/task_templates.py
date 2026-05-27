from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .agent_loop import AgentTask

DEFAULT_TEMPLATES_DIR = Path(__file__).resolve().parents[2] / "goals"


@dataclass(slots=True)
class TemplateField:
    name: str
    label: str
    required: bool = True
    help_text: str = ""
    kind: str = "text"
    default: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class GoalTemplate:
    template_id: str
    title: str
    description: str
    task_summary_template: str
    fields: list[TemplateField] = field(default_factory=list)
    vector_field: str = "vector"
    raster_field: str | None = None
    source_crs_field: str | None = None
    default_max_iterations: int = 3

    def to_dict(self) -> dict[str, Any]:
        return {
            "template_id": self.template_id,
            "title": self.title,
            "description": self.description,
            "fields": [field.to_dict() for field in self.fields],
            "vector_field": self.vector_field,
            "raster_field": self.raster_field,
            "source_crs_field": self.source_crs_field,
            "default_max_iterations": self.default_max_iterations,
        }

    def render_summary(self, values: dict[str, Any]) -> str:
        return self.task_summary_template.format(**values)

    def render_task(
        self,
        *,
        values: dict[str, Any],
        max_iterations: int | None = None,
        task_summary: str | None = None,
    ) -> AgentTask:
        missing = [
            field.name
            for field in self.fields
            if field.required and values.get(field.name) in {None, ""}
        ]
        if missing:
            raise ValueError(f"Missing required template input(s): {', '.join(missing)}")
        vector_value = values.get(self.vector_field)
        raster_value = values.get(self.raster_field) if self.raster_field else None
        source_crs_value = values.get(self.source_crs_field) if self.source_crs_field else None
        return AgentTask(
            task_summary=task_summary or self.render_summary(values),
            vector_path=str(Path(str(vector_value))),
            raster_path=str(Path(str(raster_value))) if raster_value else None,
            source_crs=str(source_crs_value) if source_crs_value else None,
            max_iterations=max_iterations or self.default_max_iterations,
            template_id=self.template_id,
            template_title=self.title,
        )


class TemplateRegistry:
    def __init__(self, templates_dir: str | Path = DEFAULT_TEMPLATES_DIR) -> None:
        self.templates_dir = Path(templates_dir)
        self._templates: dict[str, GoalTemplate] | None = None

    def _load_template(self, path: Path) -> GoalTemplate:
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        fields = [
            TemplateField(
                name=item["name"],
                label=item.get("label", item["name"]),
                required=bool(item.get("required", True)),
                help_text=item.get("help_text", ""),
                kind=item.get("kind", "text"),
                default=item.get("default"),
            )
            for item in payload.get("fields", [])
        ]
        return GoalTemplate(
            template_id=payload["template_id"],
            title=payload["title"],
            description=payload.get("description", ""),
            task_summary_template=payload["task_summary_template"],
            fields=fields,
            vector_field=payload.get("vector_field", "vector"),
            raster_field=payload.get("raster_field"),
            source_crs_field=payload.get("source_crs_field"),
            default_max_iterations=int(payload.get("default_max_iterations", 3)),
        )

    def load(self) -> dict[str, GoalTemplate]:
        if self._templates is None:
            self._templates = {}
            for path in sorted(self.templates_dir.glob("*.yaml")):
                template = self._load_template(path)
                self._templates[template.template_id] = template
        return self._templates

    def list(self) -> list[GoalTemplate]:
        return list(self.load().values())

    def get(self, template_id: str) -> GoalTemplate:
        try:
            return self.load()[template_id]
        except KeyError as exc:
            raise KeyError(f"Unknown template id: {template_id}") from exc

    def render_task(
        self,
        template_id: str,
        *,
        values: dict[str, Any],
        max_iterations: int | None = None,
        task_summary: str | None = None,
    ) -> AgentTask:
        template = self.get(template_id)
        return template.render_task(values=values, max_iterations=max_iterations, task_summary=task_summary)
