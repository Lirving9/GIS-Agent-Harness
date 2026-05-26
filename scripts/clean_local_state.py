from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from gis_agent_harness.local_ops import cleanup_local_state


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Remove local runtime artifacts and optional generated fixtures.")
    parser.add_argument(
        "--include-fixtures",
        action="store_true",
        help="Also remove tests/fixtures/ in addition to local runtime directories.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = cleanup_local_state(ROOT, include_fixtures=args.include_fixtures)
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
