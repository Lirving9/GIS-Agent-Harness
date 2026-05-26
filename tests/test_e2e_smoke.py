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
