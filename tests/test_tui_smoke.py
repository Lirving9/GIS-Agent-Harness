from __future__ import annotations

from pathlib import Path

import pytest
from textual.widgets import Button

from gis_agent_harness.agent_loop import AgentTask
from gis_agent_harness.config import HarnessConfig
from gis_agent_harness.state_store import StateSnapshot, StateStore
from gis_agent_harness.tui.app import GISAgentApp
from gis_agent_harness.tui.screens import ConfigScreen, GoalScreen, HomeScreen, RecoveryScreen
from gis_agent_harness.tui.widgets import JsonPanel


@pytest.mark.asyncio
async def test_tui_smoke_navigation(tmp_path: Path) -> None:
    config = HarnessConfig(
        run_root=tmp_path / ".runs",
        state_file=tmp_path / "AGENT_STATE.md",
        use_mock=True,
        provider="mock",
    )
    app = GISAgentApp(config=config)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert isinstance(app.screen, HomeScreen)
        app.open_goal("align_vector_to_raster")
        await pilot.pause()
        assert isinstance(app.screen, GoalScreen)
        app.open_recovery()
        await pilot.pause()
        assert isinstance(app.screen, RecoveryScreen)
        app.open_config()
        await pilot.pause()
        assert isinstance(app.screen, ConfigScreen)


@pytest.mark.asyncio
async def test_tui_replay_requires_confirmation_click(tmp_path: Path) -> None:
    config = HarnessConfig(
        run_root=tmp_path / ".runs",
        state_file=tmp_path / "AGENT_STATE.md",
        use_mock=True,
        provider="mock",
    )
    store = StateStore(config.state_file, config.run_root)
    store.append(
        StateSnapshot(
            run_id="failed-run",
            iteration=0,
            stage="start",
            status="running",
            summary="failed task",
            artifacts={
                "task": AgentTask(
                    task_summary="Replay this failed task.",
                    vector_path=str(tmp_path / "input.gpkg"),
                    max_iterations=1,
                ).to_dict()
            },
        )
    )
    store.append(
        StateSnapshot(
            run_id="failed-run",
            iteration=1,
            stage="stop",
            status="failed",
            summary="failed",
        )
    )

    replay_started = False

    class ConfirmingApp(GISAgentApp):
        def start_replay(self, *, source_crs: str | None = None, screen: object) -> None:
            nonlocal replay_started
            replay_started = True

    app = ConfirmingApp(config=config)
    async with app.run_test() as pilot:
        app.open_recovery()
        await pilot.pause()
        assert isinstance(app.screen, RecoveryScreen)

        app.screen.query_one("#recovery-replay", Button).press()
        await pilot.pause()
        assert replay_started is False

        app.screen.query_one("#recovery-replay", Button).press()
        await pilot.pause()
        assert replay_started is True


@pytest.mark.asyncio
async def test_tui_goal_invalid_max_iterations_stays_on_screen(tmp_path: Path) -> None:
    config = HarnessConfig(
        run_root=tmp_path / ".runs",
        state_file=tmp_path / "AGENT_STATE.md",
        use_mock=True,
        provider="mock",
    )
    app = GISAgentApp(config=config)
    async with app.run_test() as pilot:
        app.open_goal("align_vector_to_raster")
        await pilot.pause()
        assert isinstance(app.screen, GoalScreen)

        await pilot.click("#input-max-iterations")
        await pilot.press("a", "b", "c")
        await pilot.click("#goal-preview")
        await pilot.pause()

        assert isinstance(app.screen, GoalScreen)
        assert "max_iterations" in str(app.screen.query_one("#goal-preview-panel", JsonPanel).renderable)
