from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class ExceptionExplanation:
    code: str
    severity: str
    message: str
    suggested_fix: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "suggested_fix": self.suggested_fix,
        }


def explain_geospatial_exception(message: str) -> ExceptionExplanation:
    normalized = message.lower()
    if "topology" in normalized or "self-intersection" in normalized or "self intersection" in normalized:
        return ExceptionExplanation(
            code="invalid_geometry",
            severity="error",
            message="The geometry operation failed because at least one feature is topologically invalid.",
            suggested_fix="Run GeoSeries.make_valid(), Shapely make_valid, or a zero-distance buffer before retrying.",
        )
    if "not recognized as a supported file format" in normalized or "cple_openfailederror" in normalized:
        return ExceptionExplanation(
            code="dataset_open_failed",
            severity="error",
            message="The dataset could not be opened by GDAL/OGR with the available drivers.",
            suggested_fix="Verify the path, sidecar files, archive extraction, driver support, and file extension.",
        )
    if "crs" in normalized or "projection" in normalized:
        return ExceptionExplanation(
            code="crs_error",
            severity="error",
            message="The operation failed because coordinate reference metadata is missing or incompatible.",
            suggested_fix="Inspect source and target CRS metadata, then use set_crs only for declarations and to_crs for reprojection.",
        )
    return ExceptionExplanation(
        code="geospatial_exception",
        severity="warning",
        message="The geospatial library raised an exception that does not match a known parser rule.",
        suggested_fix="Inspect the archived script, input metadata, and library stderr before retrying.",
    )
