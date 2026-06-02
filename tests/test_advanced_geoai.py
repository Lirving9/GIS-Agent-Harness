from __future__ import annotations

import base64
import json
from pathlib import Path

from click.testing import CliRunner

from gis_agent_harness.cli import main
from gis_agent_harness.adversarial_review import run_method_review
from gis_agent_harness.benchmarking import BenchmarkTask, build_benchmark_manifest
from gis_agent_harness.cog_viewer import build_cog_viewer
from gis_agent_harness.faas_planner import build_faas_manifest
from gis_agent_harness.geo_exception_parser import explain_geospatial_exception
from gis_agent_harness.mcp_registry import build_mcp_manifest
from gis_agent_harness.parameter_alignment import align_parameters
from gis_agent_harness.pipeline_reporting import PipelineCheck, render_junit_xml
from gis_agent_harness.qgis_plugin import build_qgis_plugin_manifest
from gis_agent_harness.resource_router import route_code
from gis_agent_harness.stac_discovery import build_stac_query_plan
from gis_agent_harness.visual_artifacts import capture_visual_artifact
from gis_agent_harness.visual_judge import judge_map_product


ONE_PIXEL_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
)


def test_mcp_manifest_filters_tools_by_domain() -> None:
    manifest = build_mcp_manifest(domain="raster")

    payload = manifest.to_dict()

    assert payload["protocol"] == "mcp-json-rpc"
    assert payload["progressive_disclosure"] is True
    assert {tool["domain"] for tool in payload["tools"]} == {"raster"}
    assert "inspect_raster" in {tool["name"] for tool in payload["tools"]}


def test_parameter_alignment_normalizes_spatial_arguments() -> None:
    result = align_parameters(
        {
            "target_crs": 4326,
            "source_crs": "epsg:3857",
            "bbox": "-1.5, -2, 3.25, 4",
            "distance": "500",
        }
    )

    assert result.parameters["target_crs"] == "EPSG:4326"
    assert result.parameters["source_crs"] == "EPSG:3857"
    assert result.parameters["bbox"] == [-1.5, -2.0, 3.25, 4.0]
    assert result.parameters["distance"] == 500.0
    assert {change["field"] for change in result.changes} >= {"target_crs", "source_crs", "bbox", "distance"}


def test_visual_capture_and_judge_produce_review_feedback(tmp_path: Path) -> None:
    image_path = tmp_path / "map.png"
    image_path.write_bytes(ONE_PIXEL_PNG)

    artifact = capture_visual_artifact(image_path, output_dir=tmp_path / "captures")
    review = judge_map_product(
        artifact,
        {
            "required_layers": ["buildings", "basemap"],
            "observed_layers": ["buildings"],
            "legend_required": True,
            "legend_present": False,
        },
    )

    assert artifact.content_type == "image/png"
    assert artifact.sha256
    assert artifact.thumbnail_base64
    assert review.status == "needs_revision"
    assert {issue.code for issue in review.issues} >= {"missing_layer", "missing_legend"}


def test_stac_faas_qgis_cog_manifests_are_local_first(tmp_path: Path) -> None:
    stac_plan = build_stac_query_plan(
        collections=["sentinel-2-l2a"],
        bbox=[-60.0, -4.0, -59.0, -3.0],
        datetime_range="2023-06-01/2023-08-31",
        max_cloud_cover=20,
    )
    route = route_code("import torch\nimport rasterio\n")
    faas_manifest = build_faas_manifest(
        function_name="segment-cog",
        image="gis-agent-harness:local",
        handler="functions.segment:handler",
        input_assets=["s3://example/cog.tif"],
        resource_route=route,
    )
    qgis_manifest = build_qgis_plugin_manifest(plugin_name="GISAgentMCPBridge")
    viewer = build_cog_viewer(
        output_html=tmp_path / "viewer.html",
        cog_url="file:///tmp/result.tif",
        title="COG Review",
    )

    assert stac_plan.query["query"]["eo:cloud_cover"]["lt"] == 20
    assert stac_plan.network_required is False
    assert route.track == "gpu"
    assert faas_manifest["mode"] == "manifest-only"
    assert qgis_manifest["transport"] == "mcp-json-rpc"
    assert viewer.exists()
    assert "COG Review" in viewer.read_text(encoding="utf-8")


def test_benchmark_pipeline_and_method_review_are_serializable() -> None:
    manifest = build_benchmark_manifest(
        [
            BenchmarkTask(
                task_id="geoagentbench-crs",
                suite="GeoAgentBench",
                prompt="Align vector CRS to raster CRS.",
                expected_capabilities=["plan_and_react", "pea"],
            )
        ]
    )
    review = run_method_review(
        {
            "method": "ordinary least squares on spatial polygons",
            "crs": "EPSG:4326",
            "tests": ["significance"],
            "notes": "No spatial autocorrelation check was recorded.",
        },
        max_rounds=2,
    )
    junit = render_junit_xml(
        "geoai-acceptance",
        [
            PipelineCheck(name="stac_plan", passed=True),
            PipelineCheck(name="visual_judge", passed=False, message="missing legend"),
        ],
    )

    assert manifest["suites"]["GeoAgentBench"]["task_count"] == 1
    assert review["status"] == "needs_revision"
    assert review["rounds"] <= 2
    assert "spatial_autocorrelation" in {item["code"] for item in review["findings"]}
    assert 'testsuite name="geoai-acceptance"' in junit
    assert "missing legend" in junit


def test_geospatial_exception_parser_returns_repair_guidance() -> None:
    explanation = explain_geospatial_exception(
        "GEOSException: TopologyException: Self-intersection at or near point 0 0"
    )

    assert explanation.code == "invalid_geometry"
    assert "make_valid" in explanation.suggested_fix
    assert explanation.severity == "error"


def test_advanced_cli_commands(tmp_path: Path) -> None:
    script_path = tmp_path / "script.py"
    script_path.write_text("import cupy\n", encoding="utf-8")
    image_path = tmp_path / "map.png"
    image_path.write_bytes(ONE_PIXEL_PNG)
    junit_path = tmp_path / "checks.xml"

    runner = CliRunner()

    mcp_result = runner.invoke(main, ["mcp-tools", "--domain", "vector"])
    route_result = runner.invoke(main, ["route-resource", "--script-file", str(script_path)])
    stac_result = runner.invoke(
        main,
        [
            "stac-plan",
            "--collection",
            "sentinel-2-l2a",
            "--bbox",
            "-60,-4,-59,-3",
            "--datetime",
            "2023-06-01/2023-08-31",
            "--max-cloud-cover",
            "15",
        ],
    )
    capture_result = runner.invoke(main, ["capture-artifact", str(image_path), "--output-dir", str(tmp_path / "captures")])
    exception_result = runner.invoke(
        main,
        ["explain-exception", "CPLE_OpenFailedError: not recognized as a supported file format"],
    )
    benchmark_result = runner.invoke(main, ["benchmark-manifest", "--junit-file", str(junit_path)])

    assert mcp_result.exit_code == 0
    assert json.loads(mcp_result.output)["tools"][0]["domain"] == "vector"
    assert route_result.exit_code == 0
    assert json.loads(route_result.output)["track"] == "gpu"
    assert stac_result.exit_code == 0
    assert json.loads(stac_result.output)["query"]["query"]["eo:cloud_cover"]["lt"] == 15
    assert capture_result.exit_code == 0
    assert json.loads(capture_result.output)["content_type"] == "image/png"
    assert exception_result.exit_code == 0
    assert json.loads(exception_result.output)["code"] == "dataset_open_failed"
    assert benchmark_result.exit_code == 0
    assert junit_path.exists()
