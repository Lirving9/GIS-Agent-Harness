from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class BenchmarkTask:
    task_id: str
    suite: str
    prompt: str
    expected_capabilities: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "suite": self.suite,
            "prompt": self.prompt,
            "expected_capabilities": self.expected_capabilities,
        }


DEFAULT_TASKS = [
    BenchmarkTask(
        task_id="geoagentbench-crs-alignment",
        suite="GeoAgentBench",
        prompt="Align a vector layer to a raster CRS and verify geometry validity.",
        expected_capabilities=["plan_and_react", "pea", "sandbox_execution"],
    ),
    BenchmarkTask(
        task_id="geobenchx-unsolvable-topology",
        suite="GeoBenchX",
        prompt="Reject an impossible topology request with explicit rationale.",
        expected_capabilities=["rejection_accuracy", "guardrails"],
    ),
    BenchmarkTask(
        task_id="gisbench-qgis-render",
        suite="GIS-Bench",
        prompt="Preview a QGIS buffer render workflow and produce visual review artifacts.",
        expected_capabilities=["qgis_mcp_bridge", "visual_judge"],
    ),
]


def build_benchmark_manifest(tasks: list[BenchmarkTask] | None = None) -> dict[str, Any]:
    selected = tasks or DEFAULT_TASKS
    suites: dict[str, dict[str, Any]] = {}
    for task in selected:
        suite = suites.setdefault(task.suite, {"task_count": 0, "tasks": []})
        suite["task_count"] += 1
        suite["tasks"].append(task.to_dict())
    return {
        "mode": "local-manifest",
        "judge": "llm-as-judge-compatible",
        "suites": suites,
        "tasks": [task.to_dict() for task in selected],
    }


def run_benchmark_checks(tasks: list[BenchmarkTask] | None = None) -> dict[str, Any]:
    manifest = build_benchmark_manifest(tasks)
    checks: list[dict[str, Any]] = []
    for suite_name, suite_payload in manifest["suites"].items():
        task_count = int(suite_payload["task_count"])
        checks.append(
            {
                "suite": suite_name,
                "name": f"{suite_name} manifest task coverage",
                "passed": task_count > 0,
                "task_count": task_count,
            }
        )
    return {
        "status": "succeeded" if all(check["passed"] for check in checks) else "failed",
        "checks": checks,
    }
