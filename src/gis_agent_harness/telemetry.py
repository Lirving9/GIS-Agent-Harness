from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .logging_utils import utc_now

REDACTED_SUFFIXES = ("api_key", "token", "secret", "authorization")


def redact_payload(payload: Any) -> Any:
    if isinstance(payload, dict):
        return {
            key: ("***redacted***" if key.lower().endswith(REDACTED_SUFFIXES) else redact_payload(value))
            for key, value in payload.items()
        }
    if isinstance(payload, list):
        return [redact_payload(item) for item in payload]
    return payload


@dataclass(slots=True)
class TelemetryWriter:
    path: Path

    def emit_event(self, event_type: str, payload: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        event = {
            "timestamp": utc_now(),
            "event_type": event_type,
            "payload": redact_payload(payload),
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")

    def handle_snapshot(self, snapshot: Any) -> None:
        payload = snapshot.to_dict() if hasattr(snapshot, "to_dict") else dict(snapshot)
        self.emit_event("state_snapshot", payload)
