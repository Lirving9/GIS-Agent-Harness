from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from gis_agent_harness.agent_loop import AgentTask
from gis_agent_harness.cli import main
from gis_agent_harness.config import HarnessConfig
from gis_agent_harness.goal_runner import run_agent_task
from gis_agent_harness.telemetry import load_telemetry_events


def test_agent_loop_emits_structured_telemetry_events(tmp_path: Path, fixture_paths: dict[str, str]) -> None:
    config = HarnessConfig(
        run_root=tmp_path / ".runs",
        state_file=tmp_path / "AGENT_STATE.md",
        use_mock=True,
        timeout_seconds=20,
        max_iterations=3,
    )
    result = run_agent_task(
        AgentTask(
            task_summary="Declare the missing CRS before analysis.",
            vector_path=fixture_paths["missing_crs"],
            source_crs="EPSG:4326",
            allowed_actions=["set_crs"],
            max_iterations=3,
        ),
        config,
    )

    events = load_telemetry_events(config.telemetry_file, run_id=result.run_id)
    event_types = {item["event_type"] for item in events}

    assert result.status == "succeeded"
    assert {"state_snapshot", "task_context", "decision_review", "sandbox_execution"} <= event_types


def test_show_telemetry_command_returns_summary(tmp_path: Path, fixture_paths: dict[str, str]) -> None:
    config = HarnessConfig(
        run_root=tmp_path / ".runs",
        state_file=tmp_path / "AGENT_STATE.md",
        use_mock=True,
        timeout_seconds=20,
        max_iterations=3,
    )
    result = run_agent_task(
        AgentTask(
            task_summary="Declare the missing CRS before analysis.",
            vector_path=fixture_paths["missing_crs"],
            source_crs="EPSG:4326",
            allowed_actions=["set_crs"],
            max_iterations=3,
        ),
        config,
    )

    runner = CliRunner()
    command_result = runner.invoke(
        main,
        [
            "show-telemetry",
            "--run-root",
            str(config.run_root),
            "--run-id",
            result.run_id,
            "--summary",
        ],
    )

    assert command_result.exit_code == 0
    payload = json.loads(command_result.output)
    assert payload["run_id"] == result.run_id
    assert payload["event_counts"]["decision_review"] >= 1
    assert payload["event_counts"]["sandbox_execution"] >= 1
