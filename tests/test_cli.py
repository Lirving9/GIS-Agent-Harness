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


def test_show_state_table_command(tmp_path: Path) -> None:
    state_file = tmp_path / "AGENT_STATE.md"
    run_root = tmp_path / ".runs"
    store = StateStore(state_file, run_root)
    store.append(
        StateSnapshot(
            run_id="run-table",
            iteration=3,
            stage="stop",
            status="failed",
            summary="table summary",
        )
    )

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "show-state",
            "--format",
            "table",
            "--state-file",
            str(state_file),
            "--run-root",
            str(run_root),
        ],
    )
    assert result.exit_code == 0
    assert "run_id" in result.output
    assert "run-table" in result.output
    assert "table summary" in result.output


def test_show_state_output_file_command(tmp_path: Path) -> None:
    state_file = tmp_path / "AGENT_STATE.md"
    run_root = tmp_path / ".runs"
    output_file = tmp_path / "reports" / "state.json"
    store = StateStore(state_file, run_root)
    store.append(
        StateSnapshot(
            run_id="run-out",
            iteration=1,
            stage="observe",
            status="blocked",
            summary="written",
        )
    )

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "show-state",
            "--output-file",
            str(output_file),
            "--state-file",
            str(state_file),
            "--run-root",
            str(run_root),
        ],
    )
    assert result.exit_code == 0
    assert output_file.exists()
    payload = json.loads(output_file.read_text(encoding="utf-8"))
    assert payload[0]["run_id"] == "run-out"


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


def test_list_runs_command(tmp_path: Path) -> None:
    state_file = tmp_path / "AGENT_STATE.md"
    run_root = tmp_path / ".runs"
    store = StateStore(state_file, run_root)
    for run_id, status in (("run-12", "succeeded"), ("run-13", "failed")):
        store.append(
            StateSnapshot(
                run_id=run_id,
                iteration=0,
                stage="start",
                status="running",
                summary="task",
                artifacts={"task": {"task_summary": run_id, "vector_path": f"{run_id}.gpkg"}},
            )
        )
        store.append(
            StateSnapshot(
                run_id=run_id,
                iteration=1,
                stage="stop" if status == "failed" else "complete",
                status=status,
                summary=f"{run_id}-{status}",
                observations=[Observation(code="planning_failed", message="boom")] if status == "failed" else [],
            )
        )

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "list-runs",
            "--state-file",
            str(state_file),
            "--run-root",
            str(run_root),
        ],
    )
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload[0]["run_id"] == "run-13"
    assert payload[1]["run_id"] == "run-12"


def test_list_runs_failed_only_command(tmp_path: Path) -> None:
    state_file = tmp_path / "AGENT_STATE.md"
    run_root = tmp_path / ".runs"
    store = StateStore(state_file, run_root)
    for run_id, status in (("run-14", "succeeded"), ("run-15", "failed")):
        store.append(
            StateSnapshot(
                run_id=run_id,
                iteration=0,
                stage="start",
                status="running",
                summary="task",
                artifacts={"task": {"task_summary": run_id, "vector_path": f"{run_id}.gpkg"}},
            )
        )
        store.append(
            StateSnapshot(
                run_id=run_id,
                iteration=1,
                stage="stop" if status == "failed" else "complete",
                status=status,
                summary=f"{run_id}-{status}",
                observations=[Observation(code="planning_failed", message="boom")] if status == "failed" else [],
            )
        )

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "list-runs",
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
    assert payload[0]["run_id"] == "run-15"


def test_list_runs_table_format_command(tmp_path: Path) -> None:
    state_file = tmp_path / "AGENT_STATE.md"
    run_root = tmp_path / ".runs"
    store = StateStore(state_file, run_root)
    store.append(
        StateSnapshot(
            run_id="run-table",
            iteration=0,
            stage="start",
            status="running",
            summary="task",
            artifacts={"task": {"task_summary": "Tabular run", "vector_path": "tab.gpkg"}},
        )
    )
    store.append(
        StateSnapshot(
            run_id="run-table",
            iteration=1,
            stage="stop",
            status="failed",
            summary="failed",
            observations=[Observation(code="planning_failed", message="boom")],
        )
    )

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "list-runs",
            "--format",
            "table",
            "--state-file",
            str(state_file),
            "--run-root",
            str(run_root),
        ],
    )
    assert result.exit_code == 0
    assert "run_id" in result.output
    assert "run-table" in result.output
    assert "Tabular run" in result.output


def test_list_runs_output_file_command(tmp_path: Path) -> None:
    state_file = tmp_path / "AGENT_STATE.md"
    run_root = tmp_path / ".runs"
    output_file = tmp_path / "reports" / "runs.txt"
    store = StateStore(state_file, run_root)
    store.append(
        StateSnapshot(
            run_id="run-export",
            iteration=0,
            stage="start",
            status="running",
            summary="task",
            artifacts={"task": {"task_summary": "Export run", "vector_path": "run.gpkg"}},
        )
    )
    store.append(
        StateSnapshot(
            run_id="run-export",
            iteration=1,
            stage="stop",
            status="failed",
            summary="failed",
            observations=[Observation(code="planning_failed", message="boom")],
        )
    )

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "list-runs",
            "--format",
            "table",
            "--output-file",
            str(output_file),
            "--state-file",
            str(state_file),
            "--run-root",
            str(run_root),
        ],
    )
    assert result.exit_code == 0
    assert output_file.exists()
    assert "run-export" in output_file.read_text(encoding="utf-8")


def test_list_runs_status_stage_contains_filters(tmp_path: Path) -> None:
    state_file = tmp_path / "AGENT_STATE.md"
    run_root = tmp_path / ".runs"
    store = StateStore(state_file, run_root)
    fixtures = [
        ("run-17", "succeeded", "complete", "Aligned raster"),
        ("run-18", "failed", "stop", "Missing CRS recovery"),
        ("run-19", "failed", "stop", "Invalid geometry retry"),
    ]
    for run_id, status, stage, task_summary in fixtures:
        store.append(
            StateSnapshot(
                run_id=run_id,
                iteration=0,
                stage="start",
                status="running",
                summary="task",
                artifacts={"task": {"task_summary": task_summary, "vector_path": f"{run_id}.gpkg"}},
            )
        )
        store.append(
            StateSnapshot(
                run_id=run_id,
                iteration=1,
                stage=stage,
                status=status,
                summary=f"{run_id}-{status}",
                observations=[Observation(code="planning_failed", message="boom")] if status == "failed" else [],
            )
        )

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "list-runs",
            "--status",
            "failed",
            "--stage",
            "stop",
            "--contains",
            "geometry",
            "--state-file",
            str(state_file),
            "--run-root",
            str(run_root),
        ],
    )
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert len(payload) == 1
    assert payload[0]["run_id"] == "run-19"


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


def test_resume_hint_command_with_run_id(tmp_path: Path) -> None:
    state_file = tmp_path / "AGENT_STATE.md"
    run_root = tmp_path / ".runs"
    store = StateStore(state_file, run_root)
    for run_id in ("run-7", "run-8"):
        store.append(
            StateSnapshot(
                run_id=run_id,
                iteration=0,
                stage="start",
                status="running",
                summary="task",
                artifacts={"task": {"task_summary": run_id, "vector_path": f"{run_id}.gpkg"}},
            )
        )
        store.append(
            StateSnapshot(
                run_id=run_id,
                iteration=1,
                stage="stop",
                status="failed",
                summary=f"{run_id}-failed",
                observations=[Observation(code="planning_failed", message="boom", suggested_fix="fix it")],
            )
        )

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "resume-hint",
            "--run-id",
            "run-7",
            "--state-file",
            str(state_file),
            "--run-root",
            str(run_root),
        ],
    )
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["run_id"] == "run-7"
    assert payload["task"]["task_summary"] == "run-7"


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


def test_show_failure_files_table_command(tmp_path: Path) -> None:
    state_file = tmp_path / "AGENT_STATE.md"
    run_root = tmp_path / ".runs"
    log_dir = run_root / "logs" / "run-table"
    failed_dir = run_root / "failed"
    log_dir.mkdir(parents=True, exist_ok=True)
    failed_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / "iter-1.json").write_text("{}", encoding="utf-8")
    (failed_dir / "run-table-iter-1.py").write_text("print('bad')\n", encoding="utf-8")

    store = StateStore(state_file, run_root)
    store.append(
        StateSnapshot(
            run_id="run-table",
            iteration=0,
            stage="start",
            status="running",
            summary="task",
            artifacts={"task": {"task_summary": "table fail", "vector_path": "table.gpkg"}},
        )
    )
    store.append(
        StateSnapshot(
            run_id="run-table",
            iteration=1,
            stage="stop",
            status="failed",
            summary="failed summary",
            observations=[Observation(code="sandbox_execution_failed", message="boom")],
        )
    )

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "show-failure-files",
            "--format",
            "table",
            "--state-file",
            str(state_file),
            "--run-root",
            str(run_root),
        ],
    )
    assert result.exit_code == 0
    assert "run_id" in result.output
    assert "run-table" in result.output
    assert "failed_scripts" in result.output


def test_show_failure_files_output_file_command(tmp_path: Path) -> None:
    state_file = tmp_path / "AGENT_STATE.md"
    run_root = tmp_path / ".runs"
    output_file = tmp_path / "reports" / "failure.txt"
    log_dir = run_root / "logs" / "run-export-files"
    failed_dir = run_root / "failed"
    log_dir.mkdir(parents=True, exist_ok=True)
    failed_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / "iter-1.json").write_text("{}", encoding="utf-8")
    (failed_dir / "run-export-files-iter-1.py").write_text("print('bad')\n", encoding="utf-8")
    store = StateStore(state_file, run_root)
    store.append(
        StateSnapshot(
            run_id="run-export-files",
            iteration=0,
            stage="start",
            status="running",
            summary="task",
            artifacts={"task": {"task_summary": "Export files", "vector_path": "vector.gpkg"}},
        )
    )
    store.append(
        StateSnapshot(
            run_id="run-export-files",
            iteration=1,
            stage="stop",
            status="failed",
            summary="failed summary",
            observations=[Observation(code="sandbox_execution_failed", message="boom")],
        )
    )

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "show-failure-files",
            "--format",
            "table",
            "--output-file",
            str(output_file),
            "--state-file",
            str(state_file),
            "--run-root",
            str(run_root),
        ],
    )
    assert result.exit_code == 0
    assert output_file.exists()
    assert "run-export-files" in output_file.read_text(encoding="utf-8")


def test_show_failure_files_command_with_run_id(tmp_path: Path) -> None:
    state_file = tmp_path / "AGENT_STATE.md"
    run_root = tmp_path / ".runs"
    log_dir = run_root / "logs" / "run-9"
    failed_dir = run_root / "failed"
    log_dir.mkdir(parents=True, exist_ok=True)
    failed_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / "iter-9.json").write_text("{}", encoding="utf-8")
    (failed_dir / "run-9-iter-9.py").write_text("print('bad')\n", encoding="utf-8")
    store = StateStore(state_file, run_root)
    store.append(
        StateSnapshot(
            run_id="run-9",
            iteration=0,
            stage="start",
            status="running",
            summary="task",
            artifacts={"task": {"task_summary": "nine", "vector_path": "nine.gpkg"}},
        )
    )
    store.append(
        StateSnapshot(
            run_id="run-9",
            iteration=1,
            stage="stop",
            status="failed",
            summary="run-9 failed",
            observations=[Observation(code="sandbox_execution_failed", message="boom")],
        )
    )

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "show-failure-files",
            "--run-id",
            "run-9",
            "--state-file",
            str(state_file),
            "--run-root",
            str(run_root),
        ],
    )
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["run_id"] == "run-9"
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


def test_show_replay_table_command(tmp_path: Path) -> None:
    state_file = tmp_path / "AGENT_STATE.md"
    run_root = tmp_path / ".runs"
    store = StateStore(state_file, run_root)
    store.append(
        StateSnapshot(
            run_id="run-replay-table",
            iteration=0,
            stage="start",
            status="running",
            summary="task",
            artifacts={"task": {"task_summary": "Replay table", "vector_path": "vector.gpkg"}},
        )
    )
    store.append(
        StateSnapshot(
            run_id="run-replay-table",
            iteration=1,
            stage="stop",
            status="failed",
            summary="failed summary",
            observations=[Observation(code="planning_failed", message="boom", suggested_fix="fix source CRS")],
        )
    )

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "show-replay",
            "--format",
            "table",
            "--state-file",
            str(state_file),
            "--run-root",
            str(run_root),
        ],
    )
    assert result.exit_code == 0
    assert "run_id" in result.output
    assert "run-replay-table" in result.output
    assert "Replay table" in result.output


def test_show_replay_output_file_command(tmp_path: Path) -> None:
    state_file = tmp_path / "AGENT_STATE.md"
    run_root = tmp_path / ".runs"
    output_file = tmp_path / "reports" / "replay.txt"
    store = StateStore(state_file, run_root)
    store.append(
        StateSnapshot(
            run_id="run-replay-export",
            iteration=0,
            stage="start",
            status="running",
            summary="task",
            artifacts={"task": {"task_summary": "Replay export", "vector_path": "vector.gpkg"}},
        )
    )
    store.append(
        StateSnapshot(
            run_id="run-replay-export",
            iteration=1,
            stage="stop",
            status="failed",
            summary="failed summary",
            observations=[Observation(code="planning_failed", message="boom", suggested_fix="fix replay")],
        )
    )

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "show-replay",
            "--format",
            "table",
            "--output-file",
            str(output_file),
            "--state-file",
            str(state_file),
            "--run-root",
            str(run_root),
        ],
    )
    assert result.exit_code == 0
    assert output_file.exists()
    assert "run-replay-export" in output_file.read_text(encoding="utf-8")


def test_show_replay_command_with_run_id(tmp_path: Path) -> None:
    state_file = tmp_path / "AGENT_STATE.md"
    run_root = tmp_path / ".runs"
    store = StateStore(state_file, run_root)
    store.append(
        StateSnapshot(
            run_id="run-10",
            iteration=0,
            stage="start",
            status="running",
            summary="task",
            artifacts={"task": {"task_summary": "ten", "vector_path": "ten.gpkg"}},
        )
    )
    store.append(
        StateSnapshot(
            run_id="run-10",
            iteration=1,
            stage="stop",
            status="failed",
            summary="ten failed",
            observations=[Observation(code="planning_failed", message="boom", suggested_fix="retry")],
        )
    )

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "show-replay",
            "--run-id",
            "run-10",
            "--state-file",
            str(state_file),
            "--run-root",
            str(run_root),
        ],
    )
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["run_id"] == "run-10"
    assert "ten" in payload["rerun_command"]


def test_replay_last_command_with_override(tmp_path: Path, fixture_paths: dict[str, str]) -> None:
    state_file = tmp_path / "AGENT_STATE.md"
    run_root = tmp_path / ".runs"
    store = StateStore(state_file, run_root)
    store.append(
        StateSnapshot(
            run_id="run-6",
            iteration=0,
            stage="start",
            status="running",
            summary="task",
            artifacts={
                "task": {
                    "task_summary": "Replay missing CRS",
                    "vector_path": fixture_paths["missing_crs"],
                    "raster_path": None,
                    "source_crs": None,
                    "max_iterations": 2,
                }
            },
        )
    )
    store.append(
        StateSnapshot(
            run_id="run-6",
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
            artifacts={"current_vector_path": fixture_paths["missing_crs"]},
        )
    )

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "replay-last",
            "--state-file",
            str(state_file),
            "--run-root",
            str(run_root),
            "--source-crs",
            "EPSG:4326",
            "--mock",
            "--confirm",
        ],
    )
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["status"] == "succeeded"


def test_replay_last_command_with_run_id(tmp_path: Path, fixture_paths: dict[str, str]) -> None:
    state_file = tmp_path / "AGENT_STATE.md"
    run_root = tmp_path / ".runs"
    store = StateStore(state_file, run_root)
    store.append(
        StateSnapshot(
            run_id="run-11",
            iteration=0,
            stage="start",
            status="running",
            summary="task",
            artifacts={
                "task": {
                    "task_summary": "Replay specific run",
                    "vector_path": fixture_paths["missing_crs"],
                    "raster_path": None,
                    "source_crs": None,
                    "max_iterations": 2,
                }
            },
        )
    )
    store.append(
        StateSnapshot(
            run_id="run-11",
            iteration=1,
            stage="stop",
            status="failed",
            summary="failed summary",
            observations=[Observation(code="planning_failed", message="boom", suggested_fix="provide source CRS")],
        )
    )

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "replay-last",
            "--run-id",
            "run-11",
            "--state-file",
            str(state_file),
            "--run-root",
            str(run_root),
            "--source-crs",
            "EPSG:4326",
            "--mock",
            "--confirm",
        ],
    )
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["status"] == "succeeded"


def test_replay_last_command_dry_run(tmp_path: Path, fixture_paths: dict[str, str]) -> None:
    state_file = tmp_path / "AGENT_STATE.md"
    run_root = tmp_path / ".runs"
    store = StateStore(state_file, run_root)
    store.append(
        StateSnapshot(
            run_id="run-16",
            iteration=0,
            stage="start",
            status="running",
            summary="task",
            artifacts={
                "task": {
                    "task_summary": "Dry replay",
                    "vector_path": fixture_paths["missing_crs"],
                    "raster_path": None,
                    "source_crs": None,
                    "max_iterations": 2,
                }
            },
        )
    )
    store.append(
        StateSnapshot(
            run_id="run-16",
            iteration=1,
            stage="stop",
            status="failed",
            summary="failed summary",
            observations=[Observation(code="planning_failed", message="boom", suggested_fix="provide source CRS")],
        )
    )

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "replay-last",
            "--run-id",
            "run-16",
            "--state-file",
            str(state_file),
            "--run-root",
            str(run_root),
            "--source-crs",
            "EPSG:4326",
            "--dry-run",
        ],
    )
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["mode"] == "dry-run"
    assert payload["task"]["source_crs"] == "EPSG:4326"
    assert "gis_agent_harness.cli" in payload["rerun_command"]


def test_export_report_command(tmp_path: Path) -> None:
    state_file = tmp_path / "AGENT_STATE.md"
    run_root = tmp_path / ".runs"
    report_dir = tmp_path / "reports" / "bundle"
    log_dir = run_root / "logs" / "run-report"
    failed_dir = run_root / "failed"
    log_dir.mkdir(parents=True, exist_ok=True)
    failed_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / "iter-1.json").write_text("{}", encoding="utf-8")
    (failed_dir / "run-report-iter-1.py").write_text("print('bad')\n", encoding="utf-8")

    store = StateStore(state_file, run_root)
    store.append(
        StateSnapshot(
            run_id="run-report",
            iteration=0,
            stage="start",
            status="running",
            summary="task",
            artifacts={
                "task": {
                    "task_summary": "Bundle report",
                    "vector_path": "vector.gpkg",
                    "raster_path": "raster.tif",
                    "source_crs": "EPSG:4326",
                }
            },
        )
    )
    store.append(
        StateSnapshot(
            run_id="run-report",
            iteration=1,
            stage="stop",
            status="failed",
            summary="failed summary",
            observations=[Observation(code="planning_failed", message="boom", suggested_fix="fix bundle")],
        )
    )

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "export-report",
            "--run-id",
            "run-report",
            "--output-dir",
            str(report_dir),
            "--state-file",
            str(state_file),
            "--run-root",
            str(run_root),
        ],
    )
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["run_id"] == "run-report"
    assert (report_dir / "summary.json").exists()
    assert (report_dir / "state.json").exists()
    assert (report_dir / "state.txt").exists()
    assert (report_dir / "failure-files.txt").exists()
    assert (report_dir / "replay.txt").exists()
    assert (report_dir / "index.json").exists()
    assert (report_dir / "index.txt").exists()


def test_export_report_command_uses_default_directory(tmp_path: Path) -> None:
    state_file = tmp_path / "AGENT_STATE.md"
    run_root = tmp_path / ".runs"
    log_dir = run_root / "logs" / "run-auto"
    failed_dir = run_root / "failed"
    log_dir.mkdir(parents=True, exist_ok=True)
    failed_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / "iter-1.json").write_text("{}", encoding="utf-8")
    (failed_dir / "run-auto-iter-1.py").write_text("print('bad')\n", encoding="utf-8")

    store = StateStore(state_file, run_root)
    store.append(
        StateSnapshot(
            run_id="run-auto",
            iteration=0,
            stage="start",
            status="running",
            summary="task",
            artifacts={
                "task": {
                    "task_summary": "Auto report",
                    "vector_path": "vector.gpkg",
                    "raster_path": None,
                    "source_crs": None,
                }
            },
        )
    )
    store.append(
        StateSnapshot(
            run_id="run-auto",
            iteration=1,
            stage="stop",
            status="failed",
            summary="failed summary",
            observations=[Observation(code="planning_failed", message="boom", suggested_fix="fix auto")],
        )
    )

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "export-report",
            "--run-id",
            "run-auto",
            "--state-file",
            str(state_file),
            "--run-root",
            str(run_root),
        ],
    )
    assert result.exit_code == 0
    payload = json.loads(result.output)
    output_dir = Path(payload["output_dir"])
    assert output_dir.name.startswith("run-auto-")
    assert (output_dir / "summary.json").exists()


def test_export_report_command_latest_failed(tmp_path: Path) -> None:
    state_file = tmp_path / "AGENT_STATE.md"
    run_root = tmp_path / ".runs"
    log_dir = run_root / "logs" / "run-latest"
    failed_dir = run_root / "failed"
    log_dir.mkdir(parents=True, exist_ok=True)
    failed_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / "iter-1.json").write_text("{}", encoding="utf-8")
    (failed_dir / "run-latest-iter-1.py").write_text("print('bad')\n", encoding="utf-8")

    store = StateStore(state_file, run_root)
    store.append(
        StateSnapshot(
            run_id="run-latest",
            iteration=0,
            stage="start",
            status="running",
            summary="task",
            artifacts={
                "task": {
                    "task_summary": "Latest report",
                    "vector_path": "vector.gpkg",
                    "raster_path": None,
                    "source_crs": None,
                }
            },
        )
    )
    store.append(
        StateSnapshot(
            run_id="run-latest",
            iteration=1,
            stage="stop",
            status="failed",
            summary="failed summary",
            observations=[Observation(code="planning_failed", message="boom", suggested_fix="fix latest")],
        )
    )

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "export-report",
            "--latest-failed",
            "--state-file",
            str(state_file),
            "--run-root",
            str(run_root),
        ],
    )
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["run_id"] == "run-latest"


def test_export_report_command_rejects_conflicting_target_flags(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "export-report",
            "--run-id",
            "run-x",
            "--latest-failed",
            "--output-dir",
            str(tmp_path / "reports"),
        ],
    )
    assert result.exit_code != 0
    assert "--run-id or --latest-failed" in result.output


def test_export_report_command_only_subset(tmp_path: Path) -> None:
    state_file = tmp_path / "AGENT_STATE.md"
    run_root = tmp_path / ".runs"
    report_dir = tmp_path / "reports" / "subset"
    log_dir = run_root / "logs" / "run-subset"
    failed_dir = run_root / "failed"
    log_dir.mkdir(parents=True, exist_ok=True)
    failed_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / "iter-1.json").write_text("{}", encoding="utf-8")
    (failed_dir / "run-subset-iter-1.py").write_text("print('bad')\n", encoding="utf-8")

    store = StateStore(state_file, run_root)
    store.append(
        StateSnapshot(
            run_id="run-subset",
            iteration=0,
            stage="start",
            status="running",
            summary="task",
            artifacts={
                "task": {
                    "task_summary": "Subset report",
                    "vector_path": "vector.gpkg",
                    "raster_path": None,
                    "source_crs": None,
                }
            },
        )
    )
    store.append(
        StateSnapshot(
            run_id="run-subset",
            iteration=1,
            stage="stop",
            status="failed",
            summary="failed summary",
            observations=[Observation(code="planning_failed", message="boom", suggested_fix="fix subset")],
        )
    )

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "export-report",
            "--run-id",
            "run-subset",
            "--only",
            "summary,replay",
            "--output-dir",
            str(report_dir),
            "--state-file",
            str(state_file),
            "--run-root",
            str(run_root),
        ],
    )
    assert result.exit_code == 0
    assert (report_dir / "summary.json").exists()
    assert (report_dir / "replay.json").exists()
    assert not (report_dir / "state.json").exists()
    assert not (report_dir / "failure-files.json").exists()
    assert not (report_dir / "index.json").exists()


def test_export_report_command_rejects_unknown_section(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "export-report",
            "--run-id",
            "run-x",
            "--only",
            "summary,unknown",
            "--output-dir",
            str(tmp_path / "reports"),
        ],
    )
    assert result.exit_code != 0
    assert "Unsupported report section" in result.output


def test_replay_last_command_requires_confirm(tmp_path: Path, fixture_paths: dict[str, str]) -> None:
    state_file = tmp_path / "AGENT_STATE.md"
    run_root = tmp_path / ".runs"
    store = StateStore(state_file, run_root)
    store.append(
        StateSnapshot(
            run_id="run-20",
            iteration=0,
            stage="start",
            status="running",
            summary="task",
            artifacts={
                "task": {
                    "task_summary": "Need confirm",
                    "vector_path": fixture_paths["missing_crs"],
                    "raster_path": None,
                    "source_crs": None,
                    "max_iterations": 2,
                }
            },
        )
    )
    store.append(
        StateSnapshot(
            run_id="run-20",
            iteration=1,
            stage="stop",
            status="failed",
            summary="failed summary",
            observations=[Observation(code="planning_failed", message="boom", suggested_fix="provide source CRS")],
        )
    )

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "replay-last",
            "--run-id",
            "run-20",
            "--state-file",
            str(state_file),
            "--run-root",
            str(run_root),
            "--source-crs",
            "EPSG:4326",
            "--mock",
        ],
    )
    assert result.exit_code != 0
    assert "--confirm" in result.output


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
