from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
from click.testing import CliRunner
from shapely.geometry import Point

from gis_agent_harness.cli import main
from gis_agent_harness.spatial_context import build_spatial_repo_map, describe_spatial_dataset


def test_spatial_repo_map_marks_truncated_schema(tmp_path: Path) -> None:
    vector_path = tmp_path / "wide.gpkg"
    gdf = gpd.GeoDataFrame(
        [
            {
                "field_1": 1,
                "field_2": 2,
                "field_3": 3,
                "field_4": 4,
                "field_5": 5,
                "geometry": Point(0, 0),
            }
        ],
        crs="EPSG:4326",
    )
    gdf.to_file(vector_path, driver="GPKG")

    payload = build_spatial_repo_map(tmp_path, max_schema_fields=3).to_dict()

    dataset = next(item for item in payload["datasets"] if item["path"] == "wide.gpkg")
    assert dataset["schema_field_count"] == 5
    assert dataset["schema_truncated"] is True
    assert len(dataset["schema"]) == 3


def test_describe_spatial_dataset_returns_detail_for_single_dataset(fixture_paths: dict[str, str]) -> None:
    root = Path(fixture_paths["sample_gpkg"]).parents[1]
    relative_path = Path(fixture_paths["sample_gpkg"]).relative_to(root)

    detail = describe_spatial_dataset(root, relative_path).to_dict()

    assert detail["path"] == str(relative_path)
    assert detail["kind"] == "vector"
    assert detail["feature_count"] is not None


def test_spatial_map_command_can_return_single_dataset_detail(fixture_paths: dict[str, str]) -> None:
    root = Path(fixture_paths["sample_gpkg"]).parents[1]
    relative_path = Path(fixture_paths["sample_gpkg"]).relative_to(root)

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "spatial-map",
            str(root),
            "--dataset",
            str(relative_path),
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["path"] == str(relative_path)
    assert payload["kind"] == "vector"
