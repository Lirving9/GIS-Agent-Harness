from __future__ import annotations

from typing import Any


def run_method_review(analysis: dict[str, Any], *, max_rounds: int = 4) -> dict[str, Any]:
    text = " ".join(str(value).lower() for value in analysis.values())
    findings: list[dict[str, str]] = []
    has_autocorrelation_check = "autocorrelation" in text or "moran" in text
    negates_autocorrelation_check = any(
        phrase in text
        for phrase in (
            "no spatial autocorrelation",
            "without spatial autocorrelation",
            "no moran",
            "autocorrelation check was recorded",
        )
    )
    if not has_autocorrelation_check or negates_autocorrelation_check:
        findings.append(
            {
                "code": "spatial_autocorrelation",
                "message": "No spatial autocorrelation diagnostic was recorded.",
                "suggested_fix": "Add a Moran's I, semivariogram, or comparable spatial dependence check.",
            }
        )
    if str(analysis.get("crs", "")).upper() == "EPSG:4326" and any(
        term in text for term in ("area", "distance", "buffer", "ordinary least squares")
    ):
        findings.append(
            {
                "code": "metric_crs_required",
                "message": "Metric analysis appears to use a geographic CRS.",
                "suggested_fix": "Reproject to an appropriate projected CRS before metric calculations.",
            }
        )
    rounds = min(max(1, max_rounds), 4)
    return {
        "status": "needs_revision" if findings else "approved",
        "rounds": rounds,
        "findings": findings,
        "human_checkpoint_required": bool(findings),
    }
