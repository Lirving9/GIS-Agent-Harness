from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from gis_agent_harness.sample_data import generate_sample_data


@pytest.fixture(scope="session")
def fixture_paths() -> dict[str, str]:
    return generate_sample_data(ROOT / "tests" / "fixtures")
