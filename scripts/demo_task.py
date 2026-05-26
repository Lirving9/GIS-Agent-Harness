from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from gis_agent_harness.agent_loop import AgentLoop, AgentTask
from gis_agent_harness.config import HarnessConfig
from gis_agent_harness.llm_router import LLMRouter
from gis_agent_harness.sample_data import generate_sample_data


def main() -> None:
    fixtures = generate_sample_data(ROOT / "tests" / "fixtures")
    config = HarnessConfig.from_env()
    config.use_mock = True
    router = LLMRouter(
        primary_model=config.primary_model,
        fallback_model=config.fallback_model,
        use_mock=True,
    )
    loop = AgentLoop(config=config, router=router)
    task = AgentTask(
        task_summary="Align vector CRS to raster CRS and validate geometry.",
        vector_path=fixtures["sample_3857"],
        raster_path=fixtures["sample_raster"],
        max_iterations=3,
    )
    result = loop.run(task)
    print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    if result.status != "succeeded":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
