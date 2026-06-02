from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class CompactionResult:
    blocked: bool
    compacted_attempt_count: int
    retained_history: list[dict[str, Any]]
    system_warning: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "blocked": self.blocked,
            "compacted_attempt_count": self.compacted_attempt_count,
            "retained_history": self.retained_history,
            "system_warning": self.system_warning,
        }


def _fingerprint(attempt: dict[str, Any]) -> str:
    payload = {
        "action": attempt.get("action"),
        "parameters": attempt.get("parameters", {}),
        "status": attempt.get("status"),
    }
    return json.dumps(payload, sort_keys=True, ensure_ascii=False)


def compact_failure_history(history: list[dict[str, Any]], *, max_repeats: int = 3) -> CompactionResult:
    counts: dict[str, int] = {}
    blocked = False
    compacted_attempt_count = 0
    for attempt in history:
        if attempt.get("status") != "failed":
            continue
        fingerprint = _fingerprint(attempt)
        counts[fingerprint] = counts.get(fingerprint, 0) + 1
        if counts[fingerprint] >= max_repeats:
            blocked = True
            compacted_attempt_count = counts[fingerprint]
            break
    retained = history[-2:] if len(history) > 2 else list(history)
    warning = (
        "Repeated identical failed action detected. Stop retrying the same parameters, compact prior logs, "
        "and re-evaluate the spatial assumptions, CRS metadata, topology, and data format before replanning."
        if blocked
        else "No repeated failed action exceeded the compaction threshold."
    )
    return CompactionResult(
        blocked=blocked,
        compacted_attempt_count=compacted_attempt_count,
        retained_history=retained,
        system_warning=warning,
    )
