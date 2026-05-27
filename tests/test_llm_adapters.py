from __future__ import annotations

import sys
import types
from pathlib import Path

from gis_agent_harness.auth_config import doctor_config
from gis_agent_harness.config import HarnessConfig
from gis_agent_harness.llm_adapters import LiteLLMClient, MockLLMClient, build_llm_adapter


def test_build_llm_adapter_returns_mock_for_mock_config() -> None:
    config = HarnessConfig(use_mock=True, provider="mock")
    adapter = build_llm_adapter(config)
    assert isinstance(adapter, MockLLMClient)


def test_litellm_client_resolves_profile_alias(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_completion(**kwargs):
        captured.update(kwargs)
        message = types.SimpleNamespace(content='{"action":"noop","summary":"ok","script":"print(\\"ok\\")"}')
        choice = types.SimpleNamespace(message=message)
        return types.SimpleNamespace(choices=[choice])

    monkeypatch.setitem(sys.modules, "litellm", types.SimpleNamespace(completion=fake_completion))
    config_path = tmp_path / "litellm-config.yaml"
    config_path.write_text(
        """
model_list:
  - model_name: gis-thirdparty
    litellm_params:
      model: openai/custom-model
      api_key: demo-key
      api_base: https://example.invalid/v1
      supports_system_message: false
""".strip(),
        encoding="utf-8",
    )

    client = LiteLLMClient(config_path=config_path)
    response = client.complete(
        {
            "task_summary": "Test provider forwarding.",
            "iteration": 1,
            "current_vector_path": "vector.gpkg",
            "raster_path": None,
            "artifact_dir": "artifacts/run-x",
            "source_crs": None,
            "reference_crs": None,
            "observations": [],
        },
        model="gis-thirdparty",
    )

    assert response.startswith('{"action":"noop"')
    assert captured["model"] == "openai/custom-model"
    assert captured["api_key"] == "demo-key"
    assert captured["base_url"] == "https://example.invalid/v1"
    assert len(captured["messages"]) == 1


def test_doctor_config_reports_mock_ready() -> None:
    config = HarnessConfig(use_mock=True, provider="mock")
    payload = doctor_config(config)
    assert payload["status"] == "ok"
    assert payload["provider"] == "mock"
