from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Protocol

from .errors import AgentLoopError, Observation
from .prompts import SYSTEM_PROMPT, build_repair_prompt


@dataclass(slots=True)
class AgentDecision:
    action: str
    summary: str
    script: str
    output_vector_path: str | None
    prompt: str
    response: str
    model_used: str
    attempts: int
    fallback_used: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class SupportsCompletion(Protocol):
    def complete(self, payload: dict[str, Any], *, model: str) -> str:
        ...


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
    def __init__(self, *, api_key: str | None = None, base_url: str | None = None) -> None:
        self.api_key = api_key
        self.base_url = base_url

    def complete(self, payload: dict[str, Any], *, model: str) -> str:
        try:
            from litellm import completion
        except ImportError as exc:
            raise RuntimeError("litellm is not installed; use mock routing or install dependencies.") from exc

        prompt = build_repair_prompt(payload)
        request: dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        }
        if self.base_url:
            request["base_url"] = self.base_url
        if self.api_key:
            request["api_key"] = self.api_key
        response = completion(**request)
        return response.choices[0].message.content


class LLMRouter:
    def __init__(
        self,
        *,
        primary_model: str,
        fallback_model: str,
        api_base: str | None = None,
        api_key: str | None = None,
        retries: int = 1,
        client: SupportsCompletion | None = None,
        use_mock: bool = True,
    ) -> None:
        self.primary_model = primary_model
        self.fallback_model = fallback_model
        self.retries = retries
        if client is not None:
            self.client = client
        else:
            self.client = MockLLMClient() if use_mock else LiteLLMClient(api_key=api_key, base_url=api_base)

    def _parse_response(self, response_text: str) -> dict[str, Any]:
        text = response_text.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if "\n" in text:
                text = text.split("\n", 1)[1]
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise AgentLoopError(f"Router response was not valid JSON: {response_text}") from exc

    def plan_repair(
        self,
        *,
        task_summary: str,
        observations: list[Observation],
        current_vector_path: str | Path,
        raster_path: str | Path | None,
        run_root: str | Path,
        run_id: str,
        iteration: int,
        source_crs: str | None = None,
    ) -> AgentDecision:
        artifact_dir = Path(run_root).resolve() / "artifacts" / run_id
        payload = {
            "task_summary": task_summary,
            "iteration": iteration,
            "current_vector_path": str(current_vector_path),
            "raster_path": str(raster_path) if raster_path else None,
            "artifact_dir": str(artifact_dir),
            "source_crs": source_crs,
            "reference_crs": None,
            "observations": [item.to_dict() for item in observations],
        }
        for item in observations:
            if item.code == "crs_mismatch":
                payload["reference_crs"] = item.details.get("raster_crs")
                break

        prompt = build_repair_prompt(payload)
        attempts = 0
        last_error: Exception | None = None
        models = [self.primary_model, self.fallback_model]

        for model_index, model in enumerate(models):
            for _ in range(self.retries + 1):
                attempts += 1
                try:
                    response_text = self.client.complete(payload, model=model)
                    parsed = self._parse_response(response_text)
                    return AgentDecision(
                        action=parsed["action"],
                        summary=parsed["summary"],
                        script=parsed["script"],
                        output_vector_path=parsed.get("output_vector_path"),
                        prompt=prompt,
                        response=response_text,
                        model_used=model,
                        attempts=attempts,
                        fallback_used=model_index > 0,
                    )
                except Exception as exc:
                    last_error = exc

        raise AgentLoopError(f"Router failed after {attempts} attempts: {last_error}")
