from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from gis_agent_harness.sandbox import SandboxRunner


def main() -> None:
    run_root = ROOT / ".demo-runs" / "failure-demo"
    runner = SandboxRunner(run_root, timeout_seconds=1)

    blocked = runner.run_python(
        "import os\nos.system('echo blocked')\n",
        run_id="failure-demo",
        step_name="blocked-import",
    )
    timed_out = runner.run_python(
        "while True:\n    pass\n",
        run_id="failure-demo",
        step_name="timeout-loop",
    )

    payload = {
        "blocked": blocked.to_dict(),
        "timed_out": timed_out.to_dict(),
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    if blocked.success or not timed_out.timed_out:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
