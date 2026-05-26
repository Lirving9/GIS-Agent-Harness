from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any


class HarnessError(Exception):
    """Base error for the harness."""


class DataInspectionError(HarnessError):
    """Raised when vector or raster inspection fails."""


class GuardrailError(HarnessError):
    """Raised when a guardrail blocks execution."""


class AgentLoopError(HarnessError):
    """Raised when the agent loop cannot make progress."""


@dataclass(slots=True)
class Observation:
    code: str
    message: str
    severity: str = "error"
    suggested_fix: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def fingerprint(self) -> str:
        payload = {
            "code": self.code,
            "message": self.message,
            "suggested_fix": self.suggested_fix,
        }
        return json.dumps(payload, sort_keys=True, ensure_ascii=False)
