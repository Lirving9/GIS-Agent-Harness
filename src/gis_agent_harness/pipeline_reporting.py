from __future__ import annotations

from dataclasses import dataclass
from html import escape


@dataclass(slots=True)
class PipelineCheck:
    name: str
    passed: bool
    message: str | None = None


def render_junit_xml(suite_name: str, checks: list[PipelineCheck]) -> str:
    failures = sum(1 for check in checks if not check.passed)
    lines = [
        f'<testsuite name="{escape(suite_name)}" tests="{len(checks)}" failures="{failures}">'
    ]
    for check in checks:
        lines.append(f'  <testcase name="{escape(check.name)}">')
        if not check.passed:
            message = escape(check.message or "check failed")
            lines.append(f'    <failure message="{message}">{message}</failure>')
        lines.append("  </testcase>")
    lines.append("</testsuite>")
    return "\n".join(lines)
