from __future__ import annotations

import json
from collections import Counter
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


def load_telemetry_events(
    path: str | Path,
    *,
    run_id: str | None = None,
    event_type: str | None = None,
) -> list[dict[str, Any]]:
    telemetry_path = Path(path)
    if not telemetry_path.exists():
        return []

    events = [
        json.loads(line)
        for line in telemetry_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if run_id is not None:
        events = [item for item in events if (item.get("payload") or {}).get("run_id") == run_id]
    if event_type is not None:
        events = [item for item in events if item.get("event_type") == event_type]
    return events


def summarize_telemetry(
    path: str | Path,
    *,
    run_id: str | None = None,
    event_type: str | None = None,
) -> dict[str, Any]:
    events = load_telemetry_events(path, run_id=run_id, event_type=event_type)
    event_counts = Counter(item.get("event_type", "unknown") for item in events)
    return {
        "run_id": run_id,
        "event_type_filter": event_type,
        "event_count": len(events),
        "event_counts": dict(event_counts),
        "latest_timestamp": events[-1]["timestamp"] if events else None,
    }
