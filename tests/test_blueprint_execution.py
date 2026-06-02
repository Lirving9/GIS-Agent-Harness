from __future__ import annotations

from pathlib import Path

from gis_agent_harness.benchmarking import run_benchmark_checks
from gis_agent_harness.context_compaction import compact_failure_history
from gis_agent_harness.dag_runner import DAGExecutionPlan, DAGStep, run_dag_plan
from gis_agent_harness.mcp_runtime import call_mcp_tool
from gis_agent_harness.narrative_report import build_narrative_report
from gis_agent_harness.requirement_matrix import build_requirement_matrix


def test_mcp_runtime_dispatches_local_tools(fixture_paths: dict[str, str]) -> None:
    result = call_mcp_tool("inspect_vector", {"path": fixture_paths["sample_gpkg"], "sample_size": 1})

    assert result.success is True
    assert result.tool_name == "inspect_vector"
    assert result.payload["driver"] == "GPKG"
    assert result.payload["crs"] == "EPSG:4326"


def test_dag_runner_executes_steps_in_dependency_order(tmp_path: Path) -> None:
    output_file = tmp_path / "order.txt"
    plan = DAGExecutionPlan(
        name="ordered-local-plan",
        steps=[
            DAGStep(step_id="third", tool="write_text", parameters={"path": str(output_file), "text": "3", "append": True}, depends_on=["second"]),
            DAGStep(step_id="first", tool="write_text", parameters={"path": str(output_file), "text": "1", "append": True}),
            DAGStep(step_id="second", tool="write_text", parameters={"path": str(output_file), "text": "2", "append": True}, depends_on=["first"]),
        ],
    )

    result = run_dag_plan(plan)

    assert result.status == "succeeded"
    assert [step.step_id for step in result.steps] == ["first", "second", "third"]
    assert output_file.read_text(encoding="utf-8") == "123"


def test_context_compaction_blocks_repeated_failed_actions() -> None:
    compacted = compact_failure_history(
        [
            {"action": "gdalwarp", "parameters": {"s_srs": "bad", "t_srs": "EPSG:4326"}, "status": "failed"},
            {"action": "gdalwarp", "parameters": {"s_srs": "bad", "t_srs": "EPSG:4326"}, "status": "failed"},
            {"action": "gdalwarp", "parameters": {"s_srs": "bad", "t_srs": "EPSG:4326"}, "status": "failed"},
        ],
        max_repeats=3,
    )

    assert compacted.blocked is True
    assert compacted.compacted_attempt_count == 3
    assert "re-evaluate" in compacted.system_warning.lower()


def test_narrative_report_contains_provenance_sections(tmp_path: Path) -> None:
    report_path = tmp_path / "NARRATIVE_REPORT.md"
    payload = build_narrative_report(
        {
            "run_id": "run-1",
            "summary": "Aligned vector CRS.",
            "source_data": [{"role": "input_vector", "path": "data.gpkg", "crs": "EPSG:3857"}],
            "crs_transformations": [{"source_crs": "EPSG:3857", "target_crs": "EPSG:4326", "reason": "match raster"}],
            "actions": [{"iteration": 1, "action": "to_crs", "output_vector_path": "out.gpkg"}],
            "omitted_steps": [{"code": "no_stac_download", "reason": "fixture already local"}],
        },
        output_path=report_path,
    )

    assert report_path.exists()
    assert payload["output_path"] == str(report_path)
    text = report_path.read_text(encoding="utf-8")
    assert "# Narrative Report" in text
    assert "## Source Data" in text
    assert "EPSG:3857 -> EPSG:4326" in text


def test_requirement_matrix_and_runnable_benchmark_checks() -> None:
    matrix = build_requirement_matrix()
    checks = run_benchmark_checks()

    assert matrix["summary"]["total"] >= 20
    assert matrix["summary"]["implemented"] == matrix["summary"]["total"]
    assert checks["status"] == "succeeded"
    assert {check["suite"] for check in checks["checks"]} >= {"GeoAgentBench", "GeoBenchX", "GIS-Bench"}
