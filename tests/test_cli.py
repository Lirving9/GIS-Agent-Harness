from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from gis_agent_harness.cli import main
from gis_agent_harness.errors import Observation
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


def test_show_state_markdown_command(tmp_path: Path) -> None:
    state_file = tmp_path / "AGENT_STATE.md"
    run_root = tmp_path / ".runs"
    store = StateStore(state_file, run_root)
    store.append(
        StateSnapshot(
            run_id="run-2",
            iteration=2,
            stage="complete",
            status="succeeded",
            summary="done",
        )
    )

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "show-state",
            "--format",
            "markdown",
            "--state-file",
            str(state_file),
            "--run-root",
            str(run_root),
        ],
    )
    assert result.exit_code == 0
    assert "# Agent State" in result.output
    assert "run-2" in result.output


def test_show_state_failed_only_command(tmp_path: Path) -> None:
    state_file = tmp_path / "AGENT_STATE.md"
    run_root = tmp_path / ".runs"
    store = StateStore(state_file, run_root)
    store.append(
        StateSnapshot(
            run_id="run-ok",
            iteration=1,
            stage="complete",
            status="succeeded",
            summary="ok",
        )
    )
    store.append(
        StateSnapshot(
            run_id="run-fail",
            iteration=2,
            stage="stop",
            status="failed",
            summary="bad",
        )
    )

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "show-state",
            "--failed-only",
            "--state-file",
            str(state_file),
            "--run-root",
            str(run_root),
        ],
    )
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert len(payload) == 1
    assert payload[0]["run_id"] == "run-fail"


def test_show_state_run_id_filter_command(tmp_path: Path) -> None:
    state_file = tmp_path / "AGENT_STATE.md"
    run_root = tmp_path / ".runs"
    store = StateStore(state_file, run_root)
    store.append(
        StateSnapshot(
            run_id="run-a",
            iteration=1,
            stage="observe",
            status="blocked",
            summary="a",
        )
    )
    store.append(
        StateSnapshot(
            run_id="run-b",
            iteration=2,
            stage="stop",
            status="failed",
            summary="b",
        )
    )

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "show-state",
            "--run-id",
            "run-b",
            "--state-file",
            str(state_file),
            "--run-root",
            str(run_root),
        ],
    )
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert len(payload) == 1
    assert payload[0]["run_id"] == "run-b"


def test_resume_hint_command(tmp_path: Path) -> None:
    state_file = tmp_path / "AGENT_STATE.md"
    run_root = tmp_path / ".runs"
    store = StateStore(state_file, run_root)
    store.append(
        StateSnapshot(
            run_id="run-3",
            iteration=0,
            stage="start",
            status="running",
            summary="task",
            artifacts={"task": {"task_summary": "demo", "vector_path": "vector.gpkg"}},
        )
    )
    store.append(
        StateSnapshot(
            run_id="run-3",
            iteration=1,
            stage="stop",
            status="failed",
            summary="failed summary",
            observations=[
                Observation(
                    code="planning_failed",
                    message="boom",
                    suggested_fix="provide source CRS",
                )
            ],
            artifacts={"current_vector_path": "vector.gpkg"},
        )
    )

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "resume-hint",
            "--state-file",
            str(state_file),
            "--run-root",
            str(run_root),
        ],
    )
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["run_id"] == "run-3"
    assert payload["summary"] == "failed summary"
    assert payload["task"]["task_summary"] == "demo"
    assert payload["next_step_hint"] == "provide source CRS"


def test_show_failure_files_command(tmp_path: Path) -> None:
    state_file = tmp_path / "AGENT_STATE.md"
    run_root = tmp_path / ".runs"
    log_dir = run_root / "logs" / "run-4"
    failed_dir = run_root / "failed"
    log_dir.mkdir(parents=True, exist_ok=True)
    failed_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / "iter-1.json").write_text("{}", encoding="utf-8")
    (log_dir / "iter-1.py").write_text("print('x')\n", encoding="utf-8")
    (failed_dir / "run-4-iter-1.py").write_text("print('bad')\n", encoding="utf-8")

    store = StateStore(state_file, run_root)
    store.append(
        StateSnapshot(
            run_id="run-4",
            iteration=0,
            stage="start",
            status="running",
            summary="task",
            artifacts={"task": {"task_summary": "demo fail", "vector_path": "vector.gpkg"}},
        )
    )
    store.append(
        StateSnapshot(
            run_id="run-4",
            iteration=1,
            stage="stop",
            status="failed",
            summary="failed summary",
            observations=[
                Observation(
                    code="sandbox_execution_failed",
                    message="boom",
                    suggested_fix="inspect failed script",
                )
            ],
            artifacts={"current_vector_path": "vector.gpkg"},
        )
    )

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "show-failure-files",
            "--state-file",
            str(state_file),
            "--run-root",
            str(run_root),
        ],
    )
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["run_id"] == "run-4"
    assert payload["log_json_files"]
    assert payload["log_py_files"]
    assert payload["failed_scripts"]


def test_show_replay_command(tmp_path: Path) -> None:
    state_file = tmp_path / "AGENT_STATE.md"
    run_root = tmp_path / ".runs"
    store = StateStore(state_file, run_root)
    store.append(
        StateSnapshot(
            run_id="run-5",
            iteration=0,
            stage="start",
            status="running",
            summary="task",
            artifacts={
                "task": {
                    "task_summary": "Replay me",
                    "vector_path": "vector.gpkg",
                    "raster_path": "raster.tif",
                    "source_crs": "EPSG:4326",
                }
            },
        )
    )
    store.append(
        StateSnapshot(
            run_id="run-5",
            iteration=1,
            stage="stop",
            status="failed",
            summary="failed summary",
            observations=[
                Observation(
                    code="planning_failed",
                    message="boom",
                    suggested_fix="provide source CRS",
                )
            ],
            artifacts={"current_vector_path": "vector.gpkg"},
        )
    )

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "show-replay",
            "--state-file",
            str(state_file),
            "--run-root",
            str(run_root),
        ],
    )
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["run_id"] == "run-5"
    assert "gis_agent_harness.cli" in payload["rerun_command"]
    assert "Replay me" in payload["rerun_command"]


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


def test_run_task_command_repairs_missing_crs(tmp_path: Path, fixture_paths: dict[str, str]) -> None:
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "run-task",
            "--task-summary",
            "Declare the missing CRS",
            "--vector",
            fixture_paths["missing_crs"],
            "--source-crs",
            "EPSG:4326",
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


def test_run_task_command_fails_without_source_crs(tmp_path: Path, fixture_paths: dict[str, str]) -> None:
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "run-task",
            "--task-summary",
            "Fail without source CRS",
            "--vector",
            fixture_paths["missing_crs"],
            "--run-root",
            str(tmp_path / ".runs"),
            "--state-file",
            str(tmp_path / "AGENT_STATE.md"),
            "--mock",
            "--max-iterations",
            "2",
        ],
    )
    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert payload["status"] == "failed"
    assert "planning failed" in payload["summary"].lower()
    assert any(item["code"] == "planning_failed" for item in payload["observations"])
