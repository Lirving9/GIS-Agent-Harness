from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from gis_agent_harness.sample_data import generate_sample_data


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate local GIS fixture datasets.")
    parser.add_argument(
        "--output-dir",
        default=str(ROOT / "tests" / "fixtures"),
        help="Directory that will receive the generated vector/ and raster/ fixtures.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    fixture_dir = Path(args.output_dir)
    payload = generate_sample_data(fixture_dir)
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
