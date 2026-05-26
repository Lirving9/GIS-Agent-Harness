from __future__ import annotations

import json
from typing import Any


SYSTEM_PROMPT = (
    "You are a GIS repair planner. "
    "Return strict JSON with keys action, summary, output_vector_path, and script."
)


def build_repair_prompt(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False)
