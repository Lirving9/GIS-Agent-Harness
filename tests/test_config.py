from __future__ import annotations

from gis_agent_harness.config import HarnessConfig


def test_config_reads_live_api_env(monkeypatch) -> None:
    monkeypatch.setenv("GIS_AGENT_HARNESS_API_BASE", "https://example.invalid/v1")
    monkeypatch.setenv("GIS_AGENT_HARNESS_API_KEY", "secret-key")
    monkeypatch.setenv("GIS_AGENT_HARNESS_REASONING_EFFORT", "xhigh")

    config = HarnessConfig.from_env()

    assert config.api_base == "https://example.invalid/v1"
    assert config.api_key == "secret-key"
    assert config.reasoning_effort == "xhigh"
