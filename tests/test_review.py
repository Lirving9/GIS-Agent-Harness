from __future__ import annotations

import json
from pathlib import Path

from gis_agent_harness.agent_loop import AgentLoop, AgentTask
from gis_agent_harness.config import HarnessConfig
from gis_agent_harness.errors import Observation
from gis_agent_harness.llm_router import AgentDecision, LLMRouter
from gis_agent_harness.review import review_decision
from gis_agent_harness.state_store import StateStore


def test_review_rejects_action_outside_allowed_actions(tmp_path: Path) -> None:
    task = AgentTask(
        task_summary="Declare source CRS.",
        vector_path="vector.gpkg",
        source_crs="EPSG:4326",
        allowed_actions=["set_crs"],
    )
    decision = AgentDecision(
        action="to_crs",
        summary="Reproject the dataset.",
        script="print('wrong action')\n",
        output_vector_path=str(tmp_path / "artifacts" / "out.gpkg"),
        prompt="",
        response="{}",
        model_used="mock",
        attempts=1,
        fallback_used=False,
    )

    review = review_decision(
        task=task,
        observations=[
            Observation(
                code="missing_crs",
                message="Vector dataset has no CRS metadata.",
            )
        ],
        decision=decision,
        artifact_dir=tmp_path / "artifacts",
        review_attempt=1,
    )

    assert review.allowed is False
    assert review.route == "revise"
    assert any(item.code == "review_action_mismatch" for item in review.observations)
    assert review.weighted_score < 7.5


class FlakyReviewClient:
    def __init__(self) -> None:
        self.calls = 0

    def complete(self, payload: dict[str, object], *, model: str) -> str:
        self.calls += 1
        vector_path = Path(str(payload["current_vector_path"]))
        artifact_dir = Path(str(payload["artifact_dir"]))
        output_vector_path = artifact_dir / f"{vector_path.stem}_iter{payload['iteration']}.gpkg"
        output_vector_path.parent.mkdir(parents=True, exist_ok=True)

        if self.calls == 1:
            return json.dumps(
                {
                    "action": "to_crs",
                    "summary": "Reproject first.",
                    "output_vector_path": str(output_vector_path),
                    "script": "print('review should reject this action')\n",
                }
            )

        source_crs = payload.get("source_crs") or "EPSG:4326"
        script = f"""from pathlib import Path
import geopandas as gpd

vector_path = Path(r\"{vector_path}\")
output_path = Path(r\"{output_vector_path}\")
gdf = gpd.read_file(vector_path)
gdf = gdf.set_crs(\"{source_crs}\", allow_override=True)
output_path.parent.mkdir(parents=True, exist_ok=True)
gdf.to_file(output_path, driver=\"GPKG\")
print(output_path)
"""
        return json.dumps(
            {
                "action": "set_crs",
                "summary": "Declare the missing CRS.",
                "output_vector_path": str(output_vector_path),
                "script": script,
            }
        )


def test_agent_loop_replans_after_review_rejection(tmp_path: Path, fixture_paths: dict[str, str]) -> None:
    config = HarnessConfig(
        run_root=tmp_path / ".runs",
        state_file=tmp_path / "AGENT_STATE.md",
        use_mock=True,
        timeout_seconds=20,
        max_iterations=3,
    )
    router = LLMRouter(
        primary_model=config.primary_model,
        fallback_model=config.fallback_model,
        use_mock=True,
        client=FlakyReviewClient(),
    )
    loop = AgentLoop(config=config, router=router)
    task = AgentTask(
        task_summary="Declare the missing CRS before analysis.",
        vector_path=fixture_paths["missing_crs"],
        source_crs="EPSG:4326",
        allowed_actions=["set_crs"],
        max_iterations=3,
    )

    result = loop.run(task)

    assert result.status == "succeeded"
    assert len(result.reviews) == 2
    assert result.reviews[0].allowed is False
    assert result.reviews[1].allowed is True
    store = StateStore(config.state_file, config.run_root)
    recent = store.recent(limit=20)
    assert any(item["stage"] == "review" and item["status"] == "rejected" for item in recent)
    assert any(item["stage"] == "review" and item["status"] == "approved" for item in recent)
