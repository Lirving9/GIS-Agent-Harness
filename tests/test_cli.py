from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from gis_agent_harness.cli import main
from gis_agent_harness.state_store import StateSnapshot, StateStore


def test_cli_help() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "inspect-vector" in result.output
    assert "inspect-raster" in result.output
    assert "run-task" in result.output
    assert "show-state" in result.output


def test_inspect_vector_command(fixture_paths: dict[str, str]) -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["inspect-vector", fixture_paths["sample_gpkg"]])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["driver"] == "GPKG"
    assert payload["crs"] == "EPSG:4326"


def test_inspect_raster_command(fixture_paths: dict[str, str]) -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["inspect-raster", fixture_paths["sample_raster"]])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["width"] == 8
    assert payload["crs"] == "EPSG:4326"


def test_show_state_command(tmp_path: Path) -> None:
    state_file = tmp_path / "AGENT_STATE.md"
    run_root = tmp_path / ".runs"
    store = StateStore(state_file, run_root)
    store.append(
        StateSnapshot(
            run_id="run-1",
            iteration=1,
            stage="observe",
            status="blocked",
            summary="example",
        )
    )

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "show-state",
            "--limit",
            "1",
            "--state-file",
            str(state_file),
            "--run-root",
            str(run_root),
        ],
    )
    assert result.exit_code == 0
    assert "run-1" in result.output


def test_run_task_command(tmp_path: Path, fixture_paths: dict[str, str]) -> None:
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "run-task",
            "--task-summary",
            "Align vector CRS to raster CRS",
            "--vector",
            fixture_paths["sample_3857"],
            "--raster",
            fixture_paths["sample_raster"],
            "--run-root",
            str(tmp_path / ".runs"),
            "--state-file",
            str(tmp_path / "AGENT_STATE.md"),
            "--mock",
        ],
    )
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["status"] == "succeeded"
    assert payload["iterations"] == 1
