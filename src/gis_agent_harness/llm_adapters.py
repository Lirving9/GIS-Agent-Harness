from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from .auth_config import resolve_litellm_profile
from .config import HarnessConfig
from .prompts import SYSTEM_PROMPT, build_repair_prompt


class SupportsCompletion(Protocol):
    def complete(self, payload: dict[str, Any], *, model: str) -> str:
        ...


@dataclass(slots=True)
class ResolvedModelProfile:
    model: str
    api_key: str | None = None
    base_url: str | None = None
    supports_system_message: bool = True


class MockLLMClient:
    def __init__(self, fail_models: set[str] | None = None) -> None:
        self.fail_models = fail_models or set()

    def complete(self, payload: dict[str, Any], *, model: str) -> str:
        if model in self.fail_models:
            raise RuntimeError(f"Mock failure for model {model}")

        observation_codes = [item["code"] for item in payload["observations"]]
        vector_path = Path(payload["current_vector_path"])
        run_artifact_dir = Path(payload["artifact_dir"])
        output_vector_path = run_artifact_dir / f"{vector_path.stem}_iter{payload['iteration']}.gpkg"
        output_vector_path.parent.mkdir(parents=True, exist_ok=True)

        action = "noop"
        summary = "No repair required."
        script = "print('noop')\n"

        if "missing_crs" in observation_codes:
            source_crs = payload.get("source_crs") or payload.get("reference_crs")
            if not source_crs:
                raise RuntimeError("Missing source CRS for mock set_crs repair.")
            action = "set_crs"
            summary = f"Declare the vector CRS as {source_crs} with set_crs()."
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
        elif "crs_mismatch" in observation_codes:
            raster_path = payload.get("raster_path")
            if not raster_path:
                raise RuntimeError("Raster path is required for mock CRS repair.")
            action = "to_crs"
            summary = "Reproject the vector dataset into the raster CRS with to_crs()."
            script = f"""from pathlib import Path
import geopandas as gpd
import rasterio

vector_path = Path(r\"{vector_path}\")
raster_path = Path(r\"{raster_path}\")
output_path = Path(r\"{output_vector_path}\")
gdf = gpd.read_file(vector_path)
with rasterio.open(raster_path) as src:
    target_crs = src.crs
reprojected = gdf.to_crs(target_crs)
output_path.parent.mkdir(parents=True, exist_ok=True)
reprojected.to_file(output_path, driver=\"GPKG\")
print(output_path)
"""
        elif "invalid_geometry" in observation_codes:
            action = "make_valid"
            summary = "Repair invalid geometry with make_valid()."
            script = f"""from pathlib import Path
import geopandas as gpd
from shapely import make_valid

vector_path = Path(r\"{vector_path}\")
output_path = Path(r\"{output_vector_path}\")
gdf = gpd.read_file(vector_path)
if hasattr(gdf.geometry, "make_valid"):
    gdf.geometry = gdf.geometry.make_valid()
else:
    gdf.geometry = gdf.geometry.apply(make_valid)
output_path.parent.mkdir(parents=True, exist_ok=True)
gdf.to_file(output_path, driver=\"GPKG\")
print(output_path)
"""

        return json.dumps(
            {
                "action": action,
                "summary": summary,
                "output_vector_path": str(output_vector_path),
                "script": script,
            },
            ensure_ascii=False,
        )


class LiteLLMClient:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        reasoning_effort: str | None = None,
        config_path: str | Path | None = None,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url
        self.reasoning_effort = reasoning_effort
        self.config_path = Path(config_path) if config_path is not None else None

    def _resolve_model_profile(self, model: str) -> ResolvedModelProfile:
        profile = resolve_litellm_profile(model, self.config_path)
        if profile is None:
            return ResolvedModelProfile(
                model=model,
                api_key=self.api_key,
                base_url=self.base_url,
            )
        return ResolvedModelProfile(
            model=str(profile.get("model", model)),
            api_key=self.api_key or profile.get("api_key"),
            base_url=self.base_url or profile.get("api_base") or profile.get("base_url"),
            supports_system_message=bool(profile.get("supports_system_message", True)),
        )

    def complete(self, payload: dict[str, Any], *, model: str) -> str:
        try:
            from litellm import completion
        except ImportError as exc:
            raise RuntimeError("litellm is not installed; use mock routing or install dependencies.") from exc

        prompt = build_repair_prompt(payload)
        profile = self._resolve_model_profile(model)
        messages: list[dict[str, str]]
        if profile.supports_system_message:
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ]
        else:
            messages = [{"role": "user", "content": f"{SYSTEM_PROMPT}\n\n{prompt}"}]

        request: dict[str, Any] = {
            "model": profile.model,
            "messages": messages,
        }
        if profile.base_url:
            request["base_url"] = profile.base_url
        if profile.api_key:
            request["api_key"] = profile.api_key
        if self.reasoning_effort:
            request["reasoning_effort"] = self.reasoning_effort
        response = completion(**request)
        return response.choices[0].message.content


class OpenAICompatibleAdapter(LiteLLMClient):
    pass


class AnthropicAdapter(LiteLLMClient):
    pass


def build_llm_adapter(config: HarnessConfig) -> SupportsCompletion:
    if config.use_mock or config.provider == "mock":
        return MockLLMClient()
    if config.provider == "anthropic":
        return AnthropicAdapter(
            api_key=config.api_key,
            base_url=config.api_base,
            reasoning_effort=config.reasoning_effort,
            config_path=config.litellm_config_path,
        )
    if config.provider in {"openai_compatible", "openai"}:
        return OpenAICompatibleAdapter(
            api_key=config.api_key,
            base_url=config.api_base,
            reasoning_effort=config.reasoning_effort,
            config_path=config.litellm_config_path,
        )
    return LiteLLMClient(
        api_key=config.api_key,
        base_url=config.api_base,
        reasoning_effort=config.reasoning_effort,
        config_path=config.litellm_config_path,
    )
