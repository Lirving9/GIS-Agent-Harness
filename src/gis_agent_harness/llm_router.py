from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

from .errors import AgentLoopError, Observation
from .llm_adapters import LiteLLMClient, MockLLMClient, SupportsCompletion
from .prompts import build_repair_prompt


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


class LLMRouter:
    def __init__(
        self,
        *,
        primary_model: str,
        fallback_model: str,
        api_base: str | None = None,
        api_key: str | None = None,
        reasoning_effort: str | None = None,
        retries: int = 1,
        client: SupportsCompletion | None = None,
        client_factory: Callable[[], SupportsCompletion] | None = None,
        use_mock: bool = True,
        litellm_config_path: str | None = None,
    ) -> None:
        self.primary_model = primary_model
        self.fallback_model = fallback_model
        self.retries = retries
        if client is not None:
            self.client = client
        elif client_factory is not None:
            self.client = client_factory()
        else:
            self.client = (
                MockLLMClient()
                if use_mock
                else LiteLLMClient(
                    api_key=api_key,
                    base_url=api_base,
                    reasoning_effort=reasoning_effort,
                    config_path=litellm_config_path,
                )
            )

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
