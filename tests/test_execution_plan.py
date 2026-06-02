from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from gis_agent_harness.config import HarnessConfig
from gis_agent_harness.goal_runner import GoalRunner, GoalSpec
from gis_agent_harness.cli import main


def test_goal_runner_preview_uses_plan_defaults(tmp_path: Path, fixture_paths: dict[str, str]) -> None:
    plan_path = tmp_path / "repair-plan.yaml"
    plan_path.write_text(
        "\n".join(
            [
                "name: Declare missing CRS",
                "template_id: declare_source_crs",
                "inputs:",
                f"  vector: {fixture_paths['missing_crs']}",
                "  source_crs: EPSG:4326",
                "constraints:",
                "  max_iterations: 2",
                "  allowed_actions:",
                "    - set_crs",
                "steps:",
                "  - id: inspect",
                "    objective: Inspect the vector metadata.",
                "  - id: declare",
                "    objective: Declare the missing source CRS.",
            ]
        ),
        encoding="utf-8",
    )
    config = HarnessConfig(
        run_root=tmp_path / ".runs",
        state_file=tmp_path / "AGENT_STATE.md",
        use_mock=True,
    )
    runner = GoalRunner(config)

    preview = runner.preview(
        GoalSpec(
            template_id=None,
            inputs={},
            plan_file=plan_path,
        )
    )

    assert preview["plan"]["name"] == "Declare missing CRS"
    assert preview["task"]["template_id"] == "declare_source_crs"
    assert preview["task"]["source_crs"] == "EPSG:4326"
    assert preview["task"]["max_iterations"] == 2
    assert preview["task"]["allowed_actions"] == ["set_crs"]


def test_markdown_plan_frontmatter_is_supported(tmp_path: Path, fixture_paths: dict[str, str]) -> None:
    plan_path = tmp_path / "repair-plan.md"
    plan_path.write_text(
        "\n".join(
            [
                "---",
                "name: Markdown plan",
                "template_id: declare_source_crs",
                "inputs:",
                f"  vector: {fixture_paths['missing_crs']}",
                "  source_crs: EPSG:4326",
                "constraints:",
                "  allowed_actions:",
                "    - set_crs",
                "---",
                "# Markdown plan",
                "",
                "This file keeps the plan in Markdown while storing the machine-readable frontmatter above.",
            ]
        ),
        encoding="utf-8",
    )
    config = HarnessConfig(
        run_root=tmp_path / ".runs",
        state_file=tmp_path / "AGENT_STATE.md",
        use_mock=True,
    )
    runner = GoalRunner(config)

    preview = runner.preview(
        GoalSpec(
            template_id=None,
            inputs={},
            plan_file=plan_path,
        )
    )

    assert preview["plan"]["name"] == "Markdown plan"
    assert preview["task"]["template_id"] == "declare_source_crs"
    assert preview["task"]["source_crs"] == "EPSG:4326"


def test_goal_run_command_accepts_plan_file(tmp_path: Path, fixture_paths: dict[str, str]) -> None:
    plan_path = tmp_path / "repair-plan.yaml"
    plan_path.write_text(
        "\n".join(
            [
                "name: Goal CLI plan",
                "template_id: declare_source_crs",
                "inputs:",
                f"  vector: {fixture_paths['missing_crs']}",
                "  source_crs: EPSG:4326",
                "constraints:",
                "  max_iterations: 2",
                "  allowed_actions:",
                "    - set_crs",
            ]
        ),
        encoding="utf-8",
    )

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "goal",
            "run",
            "--plan-file",
            str(plan_path),
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
