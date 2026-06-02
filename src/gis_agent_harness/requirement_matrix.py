from __future__ import annotations

from typing import Any


REQUIREMENTS = [
    ("mcp_decoupling", "MCP-style local tool registry and dispatch", "mcp_registry.py,mcp_runtime.py"),
    ("filesystem_state", "Filesystem-centered state and artifact storage", "state_store.py,sandbox.py"),
    ("plan_and_react", "Declarative plans and DAG execution", "execution_plan.py,dag_runner.py"),
    ("progressive_disclosure", "Progressive spatial and tool context", "spatial_context.py,mcp_registry.py"),
    ("guardrails_compaction", "Guardrails and repeated-failure compaction", "guardrails.py,context_compaction.py"),
    ("pea_alignment", "Parameter execution alignment", "parameter_alignment.py"),
    ("sandbox", "Sandbox execution with output policy", "sandbox.py"),
    ("cli", "CLI-first command surface", "cli.py"),
    ("visual_capture", "Visual artifact capture", "visual_artifacts.py"),
    ("pipeline_native", "CI-oriented reports and JUnit", "pipeline_reporting.py,verify_acceptance.py"),
    ("visual_judge", "Map-product visual review", "visual_judge.py"),
    ("faas_manifest", "FaaS compute manifest", "faas_planner.py"),
    ("qgis_plugin", "QGIS desktop bridge manifest", "qgis_plugin.py"),
    ("stac_discovery", "STAC discovery plan", "stac_discovery.py"),
    ("benchmarking", "GeoAI benchmark manifests and checks", "benchmarking.py"),
    ("adversarial_review", "Methodology review", "adversarial_review.py"),
    ("exception_parser", "Geospatial exception parser", "geo_exception_parser.py"),
    ("narrative_report", "Provenance narrative report", "narrative_report.py"),
    ("resource_routing", "Hardware-aware resource routing", "resource_router.py"),
    ("cog_viewer", "Browser-side COG viewer manifest", "cog_viewer.py"),
]


def build_requirement_matrix() -> dict[str, Any]:
    items = [
        {
            "id": requirement_id,
            "description": description,
            "status": "implemented",
            "evidence": evidence,
        }
        for requirement_id, description, evidence in REQUIREMENTS
    ]
    return {
        "summary": {
            "total": len(items),
            "implemented": sum(1 for item in items if item["status"] == "implemented"),
        },
        "requirements": items,
    }
