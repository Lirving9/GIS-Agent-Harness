from __future__ import annotations

import os
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any

TRUE_VALUES = {"1", "true", "yes", "on"}


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in TRUE_VALUES


def _env_first(*names: str) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value not in {None, ""}:
            return value
    return None


def _resolve_repo_relative_path(path_value: str) -> Path:
    path = Path(path_value)
    if path.is_absolute() or path.exists():
        return path
    repo_relative = Path(__file__).resolve().parents[2] / path_value
    return repo_relative if repo_relative.exists() else path


@dataclass(slots=True)
class HarnessConfig:
    run_root: Path = Path(".runs")
    state_file: Path = Path("AGENT_STATE.md")
    primary_model: str = "mock"
    fallback_model: str = "mock"
    provider: str = "mock"
    api_base: str | None = None
    api_key: str | None = None
    reasoning_effort: str | None = None
    use_mock: bool = True
    timeout_seconds: int = 20
    max_iterations: int = 3
    litellm_config_path: Path = Path("litellm-config.yaml")
    sandbox_write_root: Path = Path(".runs/artifacts")
    telemetry_local_only: bool = True
    telemetry_file: Path = Path(".runs/telemetry.jsonl")

    def __post_init__(self) -> None:
        if self.sandbox_write_root == Path(".runs/artifacts"):
            self.sandbox_write_root = self.run_root / "artifacts"
        if self.telemetry_file == Path(".runs/telemetry.jsonl"):
            self.telemetry_file = self.run_root / "telemetry.jsonl"

    @classmethod
    def from_env(cls) -> "HarnessConfig":
        use_mock = _env_bool("GIS_AGENT_HARNESS_USE_MOCK", True)
        provider = os.getenv("GIS_AGENT_HARNESS_PROVIDER", "mock" if use_mock else "litellm").strip() or "mock"
        default_primary = "mock" if use_mock else "gis-openai"
        default_fallback = "mock" if use_mock else "gis-claude"
        run_root = Path(os.getenv("GIS_AGENT_HARNESS_RUN_ROOT", ".runs"))
        return cls(
            run_root=run_root,
            state_file=Path(os.getenv("GIS_AGENT_HARNESS_STATE_FILE", "AGENT_STATE.md")),
            primary_model=os.getenv("GIS_AGENT_HARNESS_PRIMARY_MODEL", default_primary),
            fallback_model=os.getenv("GIS_AGENT_HARNESS_FALLBACK_MODEL", default_fallback),
            provider=provider,
            api_base=_env_first(
                "GIS_AGENT_HARNESS_API_BASE",
                "OPENAI_BASE_URL",
                "OPENAI_API_BASE",
                "ANTHROPIC_API_BASE",
            ),
            api_key=_env_first(
                "GIS_AGENT_HARNESS_API_KEY",
                "OPENAI_API_KEY",
                "ANTHROPIC_API_KEY",
            ),
            reasoning_effort=os.getenv("GIS_AGENT_HARNESS_REASONING_EFFORT"),
            use_mock=use_mock,
            timeout_seconds=int(os.getenv("GIS_AGENT_HARNESS_TIMEOUT_SECONDS", "20")),
            max_iterations=int(os.getenv("GIS_AGENT_HARNESS_MAX_ITERATIONS", "3")),
            litellm_config_path=_resolve_repo_relative_path(
                os.getenv("LITELLM_CONFIG_PATH", "litellm-config.yaml")
            ),
            sandbox_write_root=Path(
                os.getenv("GIS_AGENT_HARNESS_SANDBOX_WRITE_ROOT", str(run_root / "artifacts"))
            ),
            telemetry_local_only=_env_bool("GIS_AGENT_HARNESS_TELEMETRY_LOCAL_ONLY", True),
            telemetry_file=Path(
                os.getenv("GIS_AGENT_HARNESS_TELEMETRY_FILE", str(run_root / "telemetry.jsonl"))
            ),
        )

    def copy(self) -> "HarnessConfig":
        return replace(self)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        for key in ("run_root", "state_file", "litellm_config_path", "sandbox_write_root", "telemetry_file"):
            data[key] = str(data[key])
        return data
