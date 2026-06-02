from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .visual_artifacts import VisualArtifact


@dataclass(slots=True)
class VisualIssue:
    code: str
    message: str
    suggested_fix: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "suggested_fix": self.suggested_fix,
        }


@dataclass(slots=True)
class VisualReview:
    status: str
    artifact_sha256: str
    issues: list[VisualIssue] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "artifact_sha256": self.artifact_sha256,
            "issues": [issue.to_dict() for issue in self.issues],
        }


def judge_map_product(artifact: VisualArtifact, criteria: dict[str, Any] | None = None) -> VisualReview:
    criteria = criteria or {}
    required_layers = {str(item) for item in criteria.get("required_layers", [])}
    observed_layers = {str(item) for item in criteria.get("observed_layers", [])}
    issues: list[VisualIssue] = []
    for layer in sorted(required_layers - observed_layers):
        issues.append(
            VisualIssue(
                code="missing_layer",
                message=f"Required map layer is absent from the observed output: {layer}",
                suggested_fix=f"Render the {layer} layer and confirm layer ordering before export.",
            )
        )
    if criteria.get("legend_required") and not criteria.get("legend_present"):
        issues.append(
            VisualIssue(
                code="missing_legend",
                message="The map product requires a legend, but no legend was recorded.",
                suggested_fix="Add a readable legend with class labels and units.",
            )
        )
    return VisualReview(
        status="needs_revision" if issues else "accepted",
        artifact_sha256=artifact.sha256,
        issues=issues,
    )
