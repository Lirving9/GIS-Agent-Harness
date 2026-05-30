from __future__ import annotations

from pathlib import Path

import pytest

from gis_agent_harness.errors import DataInspectionError
from gis_agent_harness.qgis_process import QGISProcessRequest, load_payload, run_qgis_process
from gis_agent_harness.spatial_context import build_spatial_repo_map
from gis_agent_harness.spatial_tools import inspect_raster, inspect_vector


def test_inspect_vector_fields(fixture_paths: dict[str, str]) -> None:
    result = inspect_vector(fixture_paths["sample_gpkg"])
    payload = result.to_dict()
    assert payload["driver"] == "GPKG"
    assert payload["crs"] == "EPSG:4326"
    assert payload["bounds"] is not None
    assert payload["schema"]["geometry"] in {"Polygon", "MultiPolygon"}
    assert payload["sample_records"]


def test_inspect_raster_fields(fixture_paths: dict[str, str]) -> None:
    result = inspect_raster(fixture_paths["sample_raster"])
    payload = result.to_dict()
    assert payload["driver"] == "GTiff"
    assert payload["count"] == 1
    assert payload["nodatavals"] == [-9999.0]
    assert len(payload["transform"]) == 6


def test_missing_vector_path_raises(tmp_path: Path) -> None:
    with pytest.raises(DataInspectionError):
        inspect_vector(tmp_path / "missing.gpkg")


def test_build_spatial_repo_map_uses_metadata_only(fixture_paths: dict[str, str]) -> None:
    root = Path(fixture_paths["sample_gpkg"]).parents[1]

    payload = build_spatial_repo_map(root).to_dict()

    assert payload["dataset_count"] >= 2
    datasets = {item["path"]: item for item in payload["datasets"]}
    vector_summary = next(item for item in datasets.values() if item["kind"] == "vector")
    raster_summary = next(item for item in datasets.values() if item["kind"] == "raster")
    assert vector_summary["crs"] == "EPSG:4326"
    assert vector_summary["feature_count"] is not None
    assert "sample_records" not in vector_summary
    assert raster_summary["raster"]["band_count"] == 1


def test_qgis_process_dry_run_payload_json() -> None:
    parameters = load_payload(payload_json='{"inputs": {"INPUT": "roads.gpkg", "DISTANCE": 500}}')
    result = run_qgis_process(
        QGISProcessRequest(algorithm="native:buffer", parameters=parameters),
        dry_run=True,
    )

    payload = result.to_dict()
    assert payload["success"] is True
    assert payload["dry_run"] is True
    assert payload["command"] == ["qgis_process", "run", "native:buffer", "-"]
    assert payload["parameters"]["inputs"]["DISTANCE"] == 500
    assert payload["risk"]["payload_bytes"] > 0
    assert payload["risk"]["parameter_count"] >= 2


def test_qgis_process_execute_requires_confirmation() -> None:
    parameters = load_payload(payload_json='{"inputs": {"INPUT": "roads.gpkg", "DISTANCE": 500}}')
    result = run_qgis_process(
        QGISProcessRequest(algorithm="native:buffer", parameters=parameters),
        dry_run=False,
        confirmed=False,
    )

    payload = result.to_dict()
    assert payload["success"] is False
    assert payload["approval_required"] is True
    assert payload["confirmed"] is False
    assert payload["observations"][0]["code"] == "qgis_process_confirmation_required"
