from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def test_demo_task_smoke() -> None:
    root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root / "src")
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
