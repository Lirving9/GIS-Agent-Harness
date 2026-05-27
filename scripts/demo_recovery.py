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

from gis_agent_harness.config import HarnessConfig
from gis_agent_harness.sample_data import generate_sample_data


def run_cli(
    args: list[str],
    *,
    env: dict[str, str],
    cwd: Path,
    expect_success: bool,
) -> dict[str, Any] | list[dict[str, Any]]:
    result = subprocess.run(
        [sys.executable, "-m", "gis_agent_harness.cli", *args],
        capture_output=True,
        text=True,
        check=False,
        env=env,
        cwd=cwd,
    )
    if expect_success and result.returncode != 0:
        raise SystemExit(result.stderr or result.stdout or f"Command failed: {' '.join(args)}")
    if not expect_success and result.returncode == 0:
        raise SystemExit(f"Command unexpectedly succeeded: {' '.join(args)}")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Command did not return JSON: {' '.join(args)}\n{result.stdout}") from exc


def main() -> None:
    config = HarnessConfig.from_env()
    if "GIS_AGENT_HARNESS_RUN_ROOT" not in os.environ:
        config.run_root = ROOT / ".demo-runs" / "recovery-demo" / ".runs"
        config.sandbox_write_root = config.run_root / "artifacts"
        config.telemetry_file = config.run_root / "telemetry.jsonl"
    if "GIS_AGENT_HARNESS_STATE_FILE" not in os.environ:
        config.state_file = ROOT / ".demo-runs" / "recovery-demo" / "AGENT_STATE.md"

    workspace_root = config.state_file.parent
    workspace_root.mkdir(parents=True, exist_ok=True)
    fixture_dir = Path(os.getenv("GIS_AGENT_HARNESS_FIXTURE_DIR", str(workspace_root / "fixtures")))
    fixtures = generate_sample_data(fixture_dir)

    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC)
    env["GIS_AGENT_HARNESS_RUN_ROOT"] = str(config.run_root)
    env["GIS_AGENT_HARNESS_STATE_FILE"] = str(config.state_file)
    env["GIS_AGENT_HARNESS_FIXTURE_DIR"] = str(fixture_dir)

    initial_failure = run_cli(
        [
            "run-task",
            "--task-summary",
            "Recover a failed missing CRS task.",
            "--vector",
            fixtures["missing_crs"],
            "--mock",
        ],
        env=env,
        cwd=workspace_root,
        expect_success=False,
    )
    if not isinstance(initial_failure, dict) or initial_failure.get("status") != "failed":
        raise SystemExit("Expected an initial failed run for the recovery demo.")

    failed_run_id = str(initial_failure["run_id"])
    run_list = run_cli(
        [
            "list-runs",
            "--failed-only",
        ],
        env=env,
        cwd=workspace_root,
        expect_success=True,
    )
    state_rows = run_cli(
        [
            "show-state",
            "--run-id",
            failed_run_id,
        ],
        env=env,
        cwd=workspace_root,
        expect_success=True,
    )
    resume_hint = run_cli(
        [
            "resume-hint",
            "--run-id",
            failed_run_id,
        ],
        env=env,
        cwd=workspace_root,
        expect_success=True,
    )
    failure_files = run_cli(
        [
            "show-failure-files",
            "--run-id",
            failed_run_id,
        ],
        env=env,
        cwd=workspace_root,
        expect_success=True,
    )
    replay_plan = run_cli(
        [
            "show-replay",
            "--run-id",
            failed_run_id,
        ],
        env=env,
        cwd=workspace_root,
        expect_success=True,
    )
    report_bundle = run_cli(
        [
            "export-report",
            "--run-id",
            failed_run_id,
        ],
        env=env,
        cwd=workspace_root,
        expect_success=True,
    )
    report_index = run_cli(
        [
            "show-report",
            "--latest",
            "--format",
            "json",
        ],
        env=env,
        cwd=workspace_root,
        expect_success=True,
    )
    dry_run = run_cli(
        [
            "replay-last",
            "--run-id",
            failed_run_id,
            "--source-crs",
            "EPSG:4326",
            "--dry-run",
            "--mock",
        ],
        env=env,
        cwd=workspace_root,
        expect_success=True,
    )
    recovery_run = run_cli(
        [
            "replay-last",
            "--run-id",
            failed_run_id,
            "--source-crs",
            "EPSG:4326",
            "--confirm",
            "--mock",
        ],
        env=env,
        cwd=workspace_root,
        expect_success=True,
    )
    if not isinstance(recovery_run, dict) or recovery_run.get("status") != "succeeded":
        raise SystemExit("Expected the replayed recovery run to succeed.")

    payload = {
        "initial_failure": initial_failure,
        "run_list": run_list,
        "state_rows": state_rows,
        "resume_hint": resume_hint,
        "failure_files": failure_files,
        "replay_plan": replay_plan,
        "report_bundle": report_bundle,
        "report_index": report_index,
        "dry_run": dry_run,
        "recovery_run": recovery_run,
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
