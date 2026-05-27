from __future__ import annotations

import sys
import types

from gis_agent_harness.llm_router import LiteLLMClient


def test_litellm_client_forwards_base_url_and_api_key(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_completion(**kwargs):
        captured.update(kwargs)
        message = types.SimpleNamespace(content='{"action":"noop","summary":"ok","script":"print(\\"ok\\")"}')
        choice = types.SimpleNamespace(message=message)
        return types.SimpleNamespace(choices=[choice])

    monkeypatch.setitem(sys.modules, "litellm", types.SimpleNamespace(completion=fake_completion))

    client = LiteLLMClient(
        api_key="test-key",
        base_url="https://example.invalid/v1",
        reasoning_effort="xhigh",
    )
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
        model="5.4xh",
    )

    assert response.startswith('{"action":"noop"')
    assert captured["model"] == "5.4xh"
    assert captured["api_key"] == "test-key"
    assert captured["base_url"] == "https://example.invalid/v1"
    assert captured["reasoning_effort"] == "xhigh"
