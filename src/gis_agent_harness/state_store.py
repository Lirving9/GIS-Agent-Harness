from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .errors import Observation
from .logging_utils import ensure_run_dirs, utc_now


@dataclass(slots=True)
class StateSnapshot:
    run_id: str
    iteration: int
    stage: str
    status: str
    summary: str
    observations: list[Observation] = field(default_factory=list)
    artifacts: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["observations"] = [item.to_dict() for item in self.observations]
        return payload


class StateStore:
    def __init__(self, state_file: str | Path, run_root: str | Path) -> None:
        self.state_file = Path(state_file)
        self.run_root = Path(run_root)
        ensure_run_dirs(self.run_root)
        self.state_jsonl = self.run_root / "state.jsonl"
        self._ensure_markdown_header()

    def _ensure_markdown_header(self) -> None:
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.state_file.exists():
            self.state_file.write_text(
                "# Agent State\n\nAppend-only run history for the GIS Agent Harness.\n",
                encoding="utf-8",
            )

    def append(self, snapshot: StateSnapshot) -> None:
        self._ensure_markdown_header()
        with self.state_jsonl.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(snapshot.to_dict(), ensure_ascii=False) + "\n")

        lines = [
            f"\n## {snapshot.timestamp} | {snapshot.run_id} | {snapshot.stage} | {snapshot.status}\n",
            f"- Iteration: {snapshot.iteration}\n",
            f"- Summary: {snapshot.summary}\n",
        ]
        if snapshot.observations:
            lines.append("- Observations:\n")
            for item in snapshot.observations:
                lines.append(
                    f"  - `{item.code}`: {item.message}"
                    + (f" Suggested fix: {item.suggested_fix}" if item.suggested_fix else "")
                    + "\n"
                )
        if snapshot.artifacts:
            lines.append(f"- Artifacts: `{json.dumps(snapshot.artifacts, ensure_ascii=False)}`\n")

        with self.state_file.open("a", encoding="utf-8") as handle:
            handle.writelines(lines)

    def _load_rows(self) -> list[dict[str, Any]]:
        if not self.state_jsonl.exists():
            return []
        return [json.loads(line) for line in self.state_jsonl.read_text(encoding="utf-8").splitlines() if line.strip()]

    def recent(
        self,
        limit: int = 5,
        *,
        run_id: str | None = None,
        status: str | None = None,
        stage: str | None = None,
        failed_only: bool = False,
    ) -> list[dict[str, Any]]:
        rows = self._load_rows()
        if run_id is not None:
            rows = [row for row in rows if row.get("run_id") == run_id]
        if status is not None:
            rows = [row for row in rows if row.get("status") == status]
        if stage is not None:
            rows = [row for row in rows if row.get("stage") == stage]
        if failed_only:
            rows = [row for row in rows if row.get("status") == "failed"]
        return rows[-limit:]

    def render_recent(
        self,
        limit: int = 5,
        *,
        run_id: str | None = None,
        status: str | None = None,
        stage: str | None = None,
        failed_only: bool = False,
    ) -> str:
        snapshots = self.recent(limit=limit, run_id=run_id, status=status, stage=stage, failed_only=failed_only)
        if not snapshots:
            return self.state_file.read_text(encoding="utf-8")
        return json.dumps(snapshots, indent=2, ensure_ascii=False)

    def render_markdown(self) -> str:
        self._ensure_markdown_header()
        return self.state_file.read_text(encoding="utf-8")
