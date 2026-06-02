from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from gis_agent_harness.sample_data import generate_sample_data


def run_command(args: list[str], *, cwd: Path, env: dict[str, str], expect_success: bool = True) -> tuple[int, str, str]:
    result = subprocess.run(
        args,
        capture_output=True,
        text=True,
        check=False,
        cwd=cwd,
        env=env,
    )
    if expect_success and result.returncode != 0:
        raise SystemExit(result.stderr or result.stdout or f"Command failed: {' '.join(args)}")
    if not expect_success and result.returncode == 0:
        raise SystemExit(f"Command unexpectedly succeeded: {' '.join(args)}")
    return result.returncode, result.stdout, result.stderr


def run_cli(
    cli_args: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
    expect_success: bool = True,
) -> tuple[int, str, str]:
    return run_command([sys.executable, "-m", "gis_agent_harness.cli", *cli_args], cwd=cwd, env=env, expect_success=expect_success)


def parse_json_output(stdout: str) -> Any:
    try:
        return json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Expected JSON output, got:\n{stdout}") from exc


def main() -> None:
    default_workspace = ROOT / ".demo-runs" / "readme-workflow"
    run_root = Path(os.getenv("GIS_AGENT_HARNESS_RUN_ROOT", str(default_workspace / ".runs")))
    state_file = Path(os.getenv("GIS_AGENT_HARNESS_STATE_FILE", str(default_workspace / "AGENT_STATE.md")))
    workspace_root = state_file.parent
    fixture_dir = Path(os.getenv("GIS_AGENT_HARNESS_FIXTURE_DIR", str(workspace_root / "fixtures")))
    reports_dir = workspace_root / "reports"

    workspace_root.mkdir(parents=True, exist_ok=True)
    fixtures = generate_sample_data(fixture_dir)
    plan_dir = workspace_root / "plans"
    plan_dir.mkdir(parents=True, exist_ok=True)
    declare_plan = plan_dir / "declare_source_crs.yaml"
    declare_plan.write_text(
        "\n".join(
            [
                "name: README plan",
                "template_id: declare_source_crs",
                "inputs:",
                f"  vector: {fixtures['missing_crs']}",
                "  source_crs: EPSG:4326",
                "constraints:",
                "  max_iterations: 2",
                "  allowed_actions:",
                "    - set_crs",
            ]
        ),
        encoding="utf-8",
    )

    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC)
    env["GIS_AGENT_HARNESS_RUN_ROOT"] = str(run_root)
    env["GIS_AGENT_HARNESS_STATE_FILE"] = str(state_file)
    env["GIS_AGENT_HARNESS_FIXTURE_DIR"] = str(fixture_dir)

    _, help_stdout, _ = run_cli(["--help"], cwd=workspace_root, env=env)
    inspect_vector = parse_json_output(
        run_cli(["inspect-vector", fixtures["sample_gpkg"]], cwd=workspace_root, env=env)[1]
    )
    inspect_raster = parse_json_output(
        run_cli(["inspect-raster", fixtures["sample_raster"]], cwd=workspace_root, env=env)[1]
    )
    templates_list = parse_json_output(run_cli(["templates", "list"], cwd=workspace_root, env=env)[1])
    goal_dry_run = parse_json_output(
        run_cli(
            [
                "goal",
                "run",
                "--template",
                "declare_source_crs",
                "--vector",
                fixtures["missing_crs"],
                "--source-crs",
                "EPSG:4326",
                "--dry-run",
            ],
            cwd=workspace_root,
            env=env,
        )[1]
    )
    goal_run = parse_json_output(
        run_cli(
            [
                "goal",
                "run",
                "--template",
                "align_vector_to_raster",
                "--vector",
                fixtures["sample_3857"],
                "--raster",
                fixtures["sample_raster"],
                "--mock",
            ],
            cwd=workspace_root,
            env=env,
        )[1]
    )
    goal_plan_run = parse_json_output(
        run_cli(
            [
                "goal",
                "run",
                "--plan-file",
                str(declare_plan),
                "--mock",
            ],
            cwd=workspace_root,
            env=env,
        )[1]
    )
    config_doctor = parse_json_output(run_cli(["config", "doctor"], cwd=workspace_root, env=env)[1])
    spatial_map_detail = parse_json_output(
        run_cli(
            ["spatial-map", str(fixture_dir), "--dataset", "vector/sample.gpkg"],
            cwd=workspace_root,
            env=env,
        )[1]
    )

    failed_run = parse_json_output(
        run_cli(
            [
                "run-task",
                "--task-summary",
                "README workflow failure case",
                "--vector",
                fixtures["missing_crs"],
                "--mock",
            ],
            cwd=workspace_root,
            env=env,
            expect_success=False,
        )[1]
    )
    failed_run_id = failed_run["run_id"]

    succeeded_run = parse_json_output(
        run_cli(
            [
                "run-task",
                "--task-summary",
                "README workflow success case",
                "--vector",
                fixtures["sample_3857"],
                "--raster",
                fixtures["sample_raster"],
                "--mock",
            ],
            cwd=workspace_root,
            env=env,
        )[1]
    )

    show_state_json = parse_json_output(run_cli(["show-state"], cwd=workspace_root, env=env)[1])
    _, show_state_table, _ = run_cli(["show-state", "--format", "table"], cwd=workspace_root, env=env)
    state_report = workspace_root / "reports" / "state.txt"
    run_cli(["show-state", "--format", "table", "--output-file", str(state_report)], cwd=workspace_root, env=env)

    failed_runs = parse_json_output(run_cli(["list-runs", "--failed-only"], cwd=workspace_root, env=env)[1])
    _, list_runs_table, _ = run_cli(["list-runs", "--format", "table"], cwd=workspace_root, env=env)
    runs_report = workspace_root / "reports" / "runs.txt"
    run_cli(["list-runs", "--format", "table", "--output-file", str(runs_report)], cwd=workspace_root, env=env)
    filtered_runs = parse_json_output(
        run_cli(["list-runs", "--status", "failed", "--stage", "stop", "--contains", "README"], cwd=workspace_root, env=env)[1]
    )

    resume_hint = parse_json_output(run_cli(["resume-hint"], cwd=workspace_root, env=env)[1])
    failure_files_json = parse_json_output(run_cli(["show-failure-files"], cwd=workspace_root, env=env)[1])
    _, failure_files_table, _ = run_cli(["show-failure-files", "--format", "table"], cwd=workspace_root, env=env)
    failure_files_report = workspace_root / "reports" / "failure-files.txt"
    run_cli(
        ["show-failure-files", "--format", "table", "--output-file", str(failure_files_report)],
        cwd=workspace_root,
        env=env,
    )

    replay_json = parse_json_output(run_cli(["show-replay"], cwd=workspace_root, env=env)[1])
    _, replay_table, _ = run_cli(["show-replay", "--format", "table"], cwd=workspace_root, env=env)
    replay_report = workspace_root / "reports" / "replay.txt"
    run_cli(["show-replay", "--format", "table", "--output-file", str(replay_report)], cwd=workspace_root, env=env)

    latest_bundle = parse_json_output(run_cli(["export-report", "--latest-failed"], cwd=workspace_root, env=env)[1])
    targeted_bundle_dir = reports_dir / "run-report"
    targeted_bundle = parse_json_output(
        run_cli(
            [
                "export-report",
                "--run-id",
                failed_run_id,
                "--output-dir",
                str(targeted_bundle_dir),
            ],
            cwd=workspace_root,
            env=env,
        )[1]
    )
    profile_bundle = parse_json_output(
        run_cli(
            [
                "export-report",
                "--run-id",
                failed_run_id,
                "--profile",
                "quick",
            ],
            cwd=workspace_root,
            env=env,
        )[1]
    )
    _, printed_index, _ = run_cli(["export-report", "--latest-failed", "--print-index"], cwd=workspace_root, env=env)
    _, latest_report_text, _ = run_cli(["show-report", "--latest"], cwd=workspace_root, env=env)
    _, targeted_replay_text, _ = run_cli(
        ["show-report", "--report-dir", str(targeted_bundle_dir), "--section", "replay"],
        cwd=workspace_root,
        env=env,
    )

    replay_dry_run = parse_json_output(
        run_cli(
            ["replay-last", "--run-id", failed_run_id, "--source-crs", "EPSG:4326", "--dry-run", "--mock"],
            cwd=workspace_root,
            env=env,
        )[1]
    )
    replay_confirm = parse_json_output(
        run_cli(
            ["replay-last", "--run-id", failed_run_id, "--source-crs", "EPSG:4326", "--confirm", "--mock"],
            cwd=workspace_root,
            env=env,
        )[1]
    )
    telemetry_summary = parse_json_output(
        run_cli(
            ["show-telemetry", "--run-root", str(run_root), "--run-id", goal_plan_run["run_id"], "--summary"],
            cwd=workspace_root,
            env=env,
        )[1]
    )

    payload = {
        "help_has_core_commands": all(
            name in help_stdout
            for name in [
                "inspect-vector",
                "inspect-raster",
                "run-task",
                "show-state",
                "show-telemetry",
                "templates",
                "goal",
                "config",
                "tui",
            ]
        ),
        "inspect_vector": inspect_vector,
        "inspect_raster": inspect_raster,
        "templates_list": templates_list,
        "goal_dry_run": goal_dry_run,
        "goal_run": goal_run,
        "goal_plan_run": goal_plan_run,
        "config_doctor": config_doctor,
        "spatial_map_detail": spatial_map_detail,
        "failed_run": failed_run,
        "succeeded_run": succeeded_run,
        "show_state_count": len(show_state_json),
        "show_state_table": show_state_table,
        "state_report_exists": state_report.exists(),
        "failed_runs": failed_runs,
        "list_runs_table": list_runs_table,
        "runs_report_exists": runs_report.exists(),
        "filtered_runs": filtered_runs,
        "resume_hint": resume_hint,
        "failure_files_json": failure_files_json,
        "failure_files_table": failure_files_table,
        "failure_files_report_exists": failure_files_report.exists(),
        "replay_json": replay_json,
        "replay_table": replay_table,
        "replay_report_exists": replay_report.exists(),
        "latest_bundle": latest_bundle,
        "targeted_bundle": targeted_bundle,
        "profile_bundle": profile_bundle,
        "printed_index": printed_index,
        "latest_report_text": latest_report_text,
        "targeted_replay_text": targeted_replay_text,
        "replay_dry_run": replay_dry_run,
        "replay_confirm": replay_confirm,
        "telemetry_summary": telemetry_summary,
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
