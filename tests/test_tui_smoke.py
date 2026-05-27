from __future__ import annotations

from pathlib import Path

import pytest

from gis_agent_harness.config import HarnessConfig
from gis_agent_harness.tui.app import GISAgentApp
from gis_agent_harness.tui.screens import ConfigScreen, GoalScreen, HomeScreen, RecoveryScreen


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
