from __future__ import annotations

from pathlib import Path

from gis_agent_harness.agent_loop import AgentLoop, AgentTask
from gis_agent_harness.config import HarnessConfig
from gis_agent_harness.guardrails import preflight_dataset_checks
from gis_agent_harness.llm_router import LLMRouter, MockLLMClient


def test_agent_loop_repairs_crs_with_fallback(tmp_path: Path, fixture_paths: dict[str, str]) -> None:
    config = HarnessConfig(
        run_root=tmp_path / ".runs",
        state_file=tmp_path / "AGENT_STATE.md",
        primary_model="mock-primary",
        fallback_model="mock-fallback",
        use_mock=True,
        timeout_seconds=20,
        max_iterations=3,
    )
    router = LLMRouter(
        primary_model=config.primary_model,
        fallback_model=config.fallback_model,
        use_mock=True,
        client=MockLLMClient(fail_models={"mock-primary"}),
    )
    loop = AgentLoop(config=config, router=router)
    task = AgentTask(
        task_summary="Align vector CRS to raster CRS.",
        vector_path=fixture_paths["sample_3857"],
        raster_path=fixture_paths["sample_raster"],
        max_iterations=3,
    )

    result = loop.run(task)

    assert result.status == "succeeded"
    assert result.decisions
    assert result.decisions[0].fallback_used is True
    observations = preflight_dataset_checks(result.final_vector_path, fixture_paths["sample_raster"])
    assert not observations
    assert "succeeded" in (config.state_file.read_text(encoding="utf-8"))


def test_agent_loop_repairs_invalid_geometry(tmp_path: Path, fixture_paths: dict[str, str]) -> None:
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
    )
    loop = AgentLoop(config=config, router=router)
    task = AgentTask(
        task_summary="Repair invalid geometry before analysis.",
        vector_path=fixture_paths["invalid_geometry"],
        max_iterations=3,
    )

    result = loop.run(task)

    assert result.status == "succeeded"
    assert not preflight_dataset_checks(result.final_vector_path)
