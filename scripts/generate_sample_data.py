from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from gis_agent_harness.sample_data import generate_sample_data


def main() -> None:
    fixture_dir = ROOT / "tests" / "fixtures"
    payload = generate_sample_data(fixture_dir)
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
