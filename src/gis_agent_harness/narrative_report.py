from __future__ import annotations

from pathlib import Path
from typing import Any


def _line(text: str = "") -> str:
    return f"{text}\n"


def build_narrative_report(adoption_report: dict[str, Any], *, output_path: str | Path) -> dict[str, Any]:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    lines.append(_line("# Narrative Report"))
    lines.append(_line())
    lines.append(_line(f"- Run ID: `{adoption_report.get('run_id', '')}`"))
    lines.append(_line(f"- Summary: {adoption_report.get('summary', '')}"))
    lines.append(_line())

    lines.append(_line("## Source Data"))
    for item in adoption_report.get("source_data", []):
        lines.append(
            _line(
                f"- `{item.get('role', '')}`: `{item.get('path', '')}`"
                f" (CRS: {item.get('crs', 'unknown')})"
            )
        )
    lines.append(_line())

    lines.append(_line("## CRS Transformations"))
    for item in adoption_report.get("crs_transformations", []):
        lines.append(
            _line(
                f"- {item.get('source_crs', '')} -> {item.get('target_crs', '')}: "
                f"{item.get('reason', '')}"
            )
        )
    lines.append(_line())

    lines.append(_line("## Actions"))
    for item in adoption_report.get("actions", []):
        lines.append(
            _line(
                f"- Iteration {item.get('iteration', '')}: `{item.get('action', '')}` "
                f"produced `{item.get('output_vector_path', '')}`"
            )
        )
    lines.append(_line())

    lines.append(_line("## Omitted Steps"))
    omitted = adoption_report.get("omitted_steps", [])
    if not omitted:
        lines.append(_line("- None recorded."))
    for item in omitted:
        lines.append(_line(f"- `{item.get('code', '')}`: {item.get('reason', '')}"))

    text = "".join(lines)
    path.write_text(text, encoding="utf-8")
    return {
        "output_path": str(path),
        "bytes": len(text.encode("utf-8")),
        "section_count": text.count("\n## "),
    }
