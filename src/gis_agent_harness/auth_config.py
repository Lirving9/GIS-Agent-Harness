from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from .config import HarnessConfig


def mask_secret(value: str | None) -> str | None:
    if value in {None, ""}:
        return value
    if len(value) <= 4:
        return "*" * len(value)
    return f"{'*' * max(len(value) - 4, 4)}{value[-4:]}"


def resolve_env_reference(value: Any) -> Any:
    if isinstance(value, str) and value.startswith("os.environ/"):
        return os.getenv(value.split("/", 1)[1])
    if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
        return os.getenv(value[2:-1])
    return value


def load_litellm_profiles(path: str | Path | None) -> dict[str, dict[str, Any]]:
    if path is None:
        return {}
    config_path = Path(path)
    if not config_path.exists():
        return {}
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    profiles: dict[str, dict[str, Any]] = {}
    for item in payload.get("model_list", []):
        if not isinstance(item, dict):
            continue
        model_name = item.get("model_name")
        params = item.get("litellm_params")
        if not isinstance(model_name, str) or not isinstance(params, dict):
            continue
        profiles[model_name] = {
            key: resolve_env_reference(value)
            for key, value in params.items()
        }
    return profiles


def resolve_litellm_profile(model_name: str, path: str | Path | None) -> dict[str, Any] | None:
    return load_litellm_profiles(path).get(model_name)


def doctor_config(config: HarnessConfig) -> dict[str, Any]:
    profiles = load_litellm_profiles(config.litellm_config_path)
    available_profiles = sorted(profiles)
    primary_profile = profiles.get(config.primary_model)
    fallback_profile = profiles.get(config.fallback_model)
    missing: list[str] = []
    warnings: list[str] = []

    if config.use_mock or config.provider == "mock":
        status = "ok"
    else:
        if config.provider in {"litellm", "openai_compatible", "openai"}:
            if primary_profile is None and not config.primary_model:
                missing.append("primary_model")
            if primary_profile is None and not config.api_key:
                missing.append("api_key_or_litellm_profile")
            if config.primary_model and primary_profile is None:
                warnings.append("primary model is not defined in litellm-config.yaml; direct model mode will be used")
            if config.fallback_model and fallback_profile is None:
                warnings.append("fallback model is not defined in litellm-config.yaml; direct model mode will be used")
        if config.provider == "openai_compatible":
            if not (config.api_base or (primary_profile or {}).get("api_base")):
                missing.append("api_base")
            if not (config.api_key or (primary_profile or {}).get("api_key")):
                missing.append("api_key")
        if config.provider == "anthropic":
            if not (config.api_key or (primary_profile or {}).get("api_key")):
                missing.append("api_key")
        status = "ok" if not missing else "needs-attention"

    return {
        "status": status,
        "provider": config.provider,
        "use_mock": config.use_mock,
        "primary_model": config.primary_model,
        "fallback_model": config.fallback_model,
        "litellm_config_path": str(config.litellm_config_path),
        "litellm_config_exists": config.litellm_config_path.exists(),
        "available_profiles": available_profiles,
        "primary_profile_found": primary_profile is not None,
        "fallback_profile_found": fallback_profile is not None,
        "api_base": config.api_base,
        "api_key_masked": mask_secret(config.api_key),
        "telemetry_file": str(config.telemetry_file),
        "sandbox_write_root": str(config.sandbox_write_root),
        "qgis_require_confirm": config.qgis_require_confirm,
        "missing": sorted(set(missing)),
        "warnings": warnings,
    }
