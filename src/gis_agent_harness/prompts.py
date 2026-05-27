from __future__ import annotations

import json
from typing import Any


SYSTEM_PROMPT = (
    "You are a GIS repair planner for a local-only harness. "
    "Return strict JSON with keys action, summary, output_vector_path, and script. "
    "Use only safe local Python with pathlib, geopandas, rasterio, shapely, and standard JSON-free prints. "
    "Do not use shell commands, network access, eval, exec, or subprocess helpers. "
    "Write repaired vector outputs under the provided artifact directory."
)


def build_repair_prompt(payload: dict[str, Any]) -> str:
    return json.dumps(
        {
            "contract": {
                "response_format": {
                    "action": "string",
                    "summary": "string",
                    "output_vector_path": "string or null",
                    "script": "python source code string",
                },
                "requirements": [
                    "preserve local-only execution",
                    "prefer set_crs for missing CRS metadata",
                    "prefer to_crs for CRS mismatch",
                    "prefer make_valid for invalid geometry",
                ],
            },
            "context": payload,
        },
        indent=2,
        ensure_ascii=False,
    )
