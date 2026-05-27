from __future__ import annotations

import json
from typing import Any

from textual.widgets import Static


def _render_payload(title: str, payload: Any) -> str:
    if payload is None or payload == "" or payload == [] or payload == {}:
        return f"{title}\n<empty>"
    return f"{title}\n{json.dumps(payload, indent=2, ensure_ascii=False)}"


class JsonPanel(Static):
    def __init__(self, title: str, payload: Any = None, *, id: str | None = None) -> None:
        super().__init__(_render_payload(title, payload), id=id)
        self.title = title

    def update_payload(self, payload: Any) -> None:
        self.update(_render_payload(self.title, payload))


class LogPanel(Static):
    def __init__(self, title: str, text: str = "", *, id: str | None = None) -> None:
        super().__init__(f"{title}\n{text or '<empty>'}", id=id)
        self.title = title

    def set_text(self, text: str) -> None:
        self.update(f"{self.title}\n{text or '<empty>'}")


class RiskPreviewPanel(JsonPanel):
    pass
