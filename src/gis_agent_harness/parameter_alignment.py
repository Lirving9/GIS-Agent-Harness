from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


EPSG_FIELDS = {"crs", "source_crs", "target_crs", "reference_crs"}
FLOAT_FIELDS = {"distance", "buffer_distance", "resolution", "cell_size"}


@dataclass(slots=True)
class AlignmentResult:
    parameters: dict[str, Any]
    changes: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "parameters": self.parameters,
            "changes": self.changes,
        }


def _normalize_epsg(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    match = re.fullmatch(r"(?i)(?:epsg\s*:?\s*)?(\d{3,6})", text)
    if not match:
        return text
    return f"EPSG:{match.group(1)}"


def _normalize_bbox(value: Any) -> list[float] | Any:
    if isinstance(value, str):
        parts = [part.strip() for part in value.split(",")]
    elif isinstance(value, (list, tuple)):
        parts = list(value)
    else:
        return value
    if len(parts) != 4:
        return value
    try:
        return [float(part) for part in parts]
    except (TypeError, ValueError):
        return value


def _normalize_float(value: Any) -> float | Any:
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return value
    return value


def align_parameters(parameters: dict[str, Any]) -> AlignmentResult:
    aligned = dict(parameters)
    changes: list[dict[str, Any]] = []
    for field, value in list(aligned.items()):
        normalized = value
        if field in EPSG_FIELDS:
            normalized = _normalize_epsg(value)
        elif field == "bbox":
            normalized = _normalize_bbox(value)
        elif field in FLOAT_FIELDS:
            normalized = _normalize_float(value)
        if normalized != value:
            aligned[field] = normalized
            changes.append({"field": field, "before": value, "after": normalized})
    return AlignmentResult(parameters=aligned, changes=changes)
