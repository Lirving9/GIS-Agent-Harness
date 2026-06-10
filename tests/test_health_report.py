from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from click.testing import CliRunner

from gis_agent_harness.cli import main
from gis_agent_harness.health_report import build_health_report, render_health_report_markdown


def test_health_report_builds_at_least_fifty_local_checks() -> None:
    root = Path(__file__).resolve().parents[1]

    report = build_health_report(root)
    payload = report.to_dict()

    assert payload["check_count"] >= 50
    assert payload["summary"]["total"] == payload["check_count"]
    assert payload["summary"]["by_status"]["passed"] >= 45
    assert {
        "cli_help_fast",
        "acceptance_audit_script",
        "state_jsonl_append_only",
        "no_external_service_mvp",
        "fixture_mutation_guard",
        "cli_project_metrics",
        "readme_project_metrics_command",
        "readme_project_metrics_markdown_command",
        "readme_project_metrics_strict_command",
        "readme_project_metrics_top_files_command",
        "acceptance_project_metrics",
        "acceptance_project_metrics_markdown",
        "acceptance_project_metrics_strict_gate",
        "acceptance_project_metrics_top_files",
    } <= {item["check_id"] for item in payload["checks"]}


def test_health_report_category_filter_keeps_summary_consistent() -> None:
    root = Path(__file__).resolve().parents[1]

    report = build_health_report(root, category="testing")
    payload = report.to_dict()

    assert payload["category_filter"] == "testing"
    assert payload["check_count"] >= 8
    assert {item["category"] for item in payload["checks"]} == {"testing"}
    assert payload["summary"]["total"] == payload["check_count"]


def test_health_report_markdown_renderer_includes_actions() -> None:
    root = Path(__file__).resolve().parents[1]
    report = build_health_report(root, category="documentation")

    markdown = render_health_report_markdown(report)

    assert markdown.startswith("# GIS Agent Harness Health Report")
    assert "## Summary" in markdown
    assert "| Check | Status | Severity | Evidence | Recommendation |" in markdown
    assert "README command catalog" in markdown


def test_health_report_command_writes_json_output_file(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    output_file = tmp_path / "reports" / "health.json"
    runner = CliRunner()

    result = runner.invoke(
        main,
        [
            "health-report",
            "--root",
            str(root),
            "--category",
            "cli",
            "--output-file",
            str(output_file),
        ],
    )

    assert result.exit_code == 0
    assert output_file.exists()
    payload = json.loads(output_file.read_text(encoding="utf-8"))
    assert payload["category_filter"] == "cli"
    assert payload["summary"]["total"] == payload["check_count"]
    assert all(item["category"] == "cli" for item in payload["checks"])


def test_health_report_command_renders_markdown() -> None:
    root = Path(__file__).resolve().parents[1]
    runner = CliRunner()

    result = runner.invoke(
        main,
        [
            "health-report",
            "--root",
            str(root),
            "--format",
            "markdown",
            "--category",
            "operations",
        ],
    )

    assert result.exit_code == 0
    assert "# GIS Agent Harness Health Report" in result.output
    assert "append-only state logging" in result.output


def test_health_report_cli_import_does_not_load_heavy_gis_dependencies() -> None:
    code = """
import json
import sys
import gis_agent_harness.cli

print(json.dumps({
    name: name in sys.modules
    for name in ("fiona", "geopandas", "rasterio")
}, sort_keys=True))
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        check=True,
        text=True,
    )

    assert json.loads(result.stdout) == {"fiona": False, "geopandas": False, "rasterio": False}
