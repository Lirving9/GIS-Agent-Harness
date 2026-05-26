from __future__ import annotations

from pathlib import Path

import pytest

from gis_agent_harness.errors import DataInspectionError
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
