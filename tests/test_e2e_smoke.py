from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def test_demo_task_smoke() -> None:
    root = Path(__file__).resolve().parents[1]
    state_dir = root / ".pytest-smoke"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root / "src")
    env["GIS_AGENT_HARNESS_RUN_ROOT"] = str(state_dir / ".runs")
    env["GIS_AGENT_HARNESS_STATE_FILE"] = str(state_dir / "AGENT_STATE.md")
    env["GIS_AGENT_HARNESS_FIXTURE_DIR"] = str(state_dir / "fixtures")

    for _ in range(2):
        result = subprocess.run(
            [sys.executable, str(root / "scripts" / "demo_task.py")],
            capture_output=True,
            text=True,
            check=False,
            env=env,
            cwd=root,
        )
        assert result.returncode == 0, result.stderr
        payload = json.loads(result.stdout)
        assert payload["status"] == "succeeded"


def test_generate_sample_data_script_supports_isolated_output() -> None:
    root = Path(__file__).resolve().parents[1]
    output_dir = root / ".pytest-smoke" / "isolated-fixtures"
    result = subprocess.run(
        [
            sys.executable,
            str(root / "scripts" / "generate_sample_data.py"),
            "--output-dir",
            str(output_dir),
        ],
        capture_output=True,
        text=True,
        check=False,
        env={"PYTHONPATH": str(root / "src"), **os.environ},
        cwd=root,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["sample_gpkg"].startswith(str(output_dir))
    assert (output_dir / "vector" / "sample.gpkg").exists()


def test_demo_failures_script_smoke() -> None:
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, str(root / "scripts" / "demo_failures.py")],
        capture_output=True,
        text=True,
        check=False,
        env={"PYTHONPATH": str(root / "src"), **os.environ},
        cwd=root,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["blocked"]["blocked_by_guardrails"] is True
    assert payload["timed_out"]["timed_out"] is True


def test_demo_recovery_script_smoke() -> None:
    root = Path(__file__).resolve().parents[1]
    state_dir = root / ".pytest-smoke" / "recovery"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root / "src")
    env["GIS_AGENT_HARNESS_RUN_ROOT"] = str(state_dir / ".runs")
    env["GIS_AGENT_HARNESS_STATE_FILE"] = str(state_dir / "AGENT_STATE.md")
    env["GIS_AGENT_HARNESS_FIXTURE_DIR"] = str(state_dir / "fixtures")

    result = subprocess.run(
        [sys.executable, str(root / "scripts" / "demo_recovery.py")],
        capture_output=True,
        text=True,
        check=False,
        env=env,
        cwd=root,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["initial_failure"]["status"] == "failed"
    assert payload["resume_hint"]["run_id"] == payload["initial_failure"]["run_id"]
    assert payload["run_list"][0]["run_id"] == payload["initial_failure"]["run_id"]
    assert payload["dry_run"]["mode"] == "dry-run"
    assert payload["report_index"]["run_id"] == payload["initial_failure"]["run_id"]
    assert payload["recovery_run"]["status"] == "succeeded"


def test_demo_readme_workflow_script_smoke() -> None:
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, str(root / "scripts" / "demo_readme_workflow.py")],
        capture_output=True,
        text=True,
        check=False,
        env={"PYTHONPATH": str(root / "src"), **os.environ},
        cwd=root,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["help_has_core_commands"] is True
    assert payload["inspect_vector"]["driver"] == "GPKG"
    assert payload["inspect_raster"]["crs"] == "EPSG:4326"
    assert any(item["template_id"] == "align_vector_to_raster" for item in payload["templates_list"])
    assert payload["goal_dry_run"]["task"]["template_id"] == "declare_source_crs"
    assert payload["goal_run"]["status"] == "succeeded"
    assert payload["config_doctor"]["status"] == "ok"
    assert payload["failed_run"]["status"] == "failed"
    assert payload["succeeded_run"]["status"] == "succeeded"
    assert payload["state_report_exists"] is True
    assert payload["runs_report_exists"] is True
    assert payload["failure_files_report_exists"] is True
    assert payload["replay_report_exists"] is True
    assert payload["latest_bundle"]["run_id"] == payload["failed_run"]["run_id"]
    assert payload["targeted_bundle"]["run_id"] == payload["failed_run"]["run_id"]
    assert payload["profile_bundle"]["run_id"] == payload["failed_run"]["run_id"]
    assert "run_id:" in payload["printed_index"]
    assert "run_id:" in payload["latest_report_text"]
    assert "task_summary" in payload["targeted_replay_text"]
    assert payload["replay_dry_run"]["mode"] == "dry-run"
    assert payload["replay_confirm"]["status"] == "succeeded"


def test_verify_acceptance_script_smoke() -> None:
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, str(root / "scripts" / "verify_acceptance.py"), "--skip-pytest"],
        capture_output=True,
        text=True,
        check=False,
        env={"PYTHONPATH": str(root / "src"), **os.environ},
        cwd=root,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert all(payload["deliverables"].values())
    assert all(payload["acceptance"].values())
    assert payload["acceptance"]["project_metrics"] is True
    assert payload["evidence"]["project_metrics"]["targets"]["python_lines"]["met"] is True
    assert payload["acceptance"]["project_metrics_markdown"] is True
    assert "# GIS Agent Harness Project Metrics" in payload["evidence"]["project_metrics_markdown"]
    assert payload["acceptance"]["project_metrics_strict_gate"] is True
    assert payload["evidence"]["project_metrics_strict_gate"]["returncode"] == 1
    assert payload["evidence"]["project_metrics_strict_gate"]["payload"]["targets"]["commits"]["met"] is False
    assert payload["stop_conditions"]["all_acceptance_items"] is True
    assert payload["stop_conditions"]["readme_commands_copyable"] is True
    assert payload["stop_conditions"]["deliverables_present"] is True
