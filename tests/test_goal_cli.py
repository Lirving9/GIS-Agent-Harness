from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from gis_agent_harness.cli import main


def test_templates_list_command() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["templates", "list"])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    template_ids = {item["template_id"] for item in payload}
    assert "align_vector_to_raster" in template_ids


def test_goal_run_dry_run_command(fixture_paths: dict[str, str]) -> None:
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "goal",
            "run",
            "--template",
            "align_vector_to_raster",
            "--vector",
            fixture_paths["sample_3857"],
            "--raster",
            fixture_paths["sample_raster"],
            "--dry-run",
        ],
    )
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["task"]["template_id"] == "align_vector_to_raster"
    assert payload["task"]["raster_path"] == fixture_paths["sample_raster"]


def test_goal_run_command_executes_existing_loop(tmp_path: Path, fixture_paths: dict[str, str]) -> None:
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "goal",
            "run",
            "--template",
            "align_vector_to_raster",
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
