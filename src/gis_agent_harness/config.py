from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(slots=True)
class HarnessConfig:
    run_root: Path = Path(".runs")
    state_file: Path = Path("AGENT_STATE.md")
    primary_model: str = "mock-primary"
    fallback_model: str = "mock-fallback"
    use_mock: bool = True
    timeout_seconds: int = 20
    max_iterations: int = 3

    @classmethod
    def from_env(cls) -> "HarnessConfig":
        return cls(
            run_root=Path(os.getenv("GIS_AGENT_HARNESS_RUN_ROOT", ".runs")),
            state_file=Path(os.getenv("GIS_AGENT_HARNESS_STATE_FILE", "AGENT_STATE.md")),
            primary_model=os.getenv("GIS_AGENT_HARNESS_PRIMARY_MODEL", "mock-primary"),
            fallback_model=os.getenv("GIS_AGENT_HARNESS_FALLBACK_MODEL", "mock-fallback"),
            use_mock=os.getenv("GIS_AGENT_HARNESS_USE_MOCK", "true").lower() in {"1", "true", "yes"},
            timeout_seconds=int(os.getenv("GIS_AGENT_HARNESS_TIMEOUT_SECONDS", "20")),
            max_iterations=int(os.getenv("GIS_AGENT_HARNESS_MAX_ITERATIONS", "3")),
        )

    def to_dict(self) -> dict[str, str | int | bool]:
        data = asdict(self)
        data["run_root"] = str(self.run_root)
        data["state_file"] = str(self.state_file)
        return data
