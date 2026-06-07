from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from click.testing import CliRunner

from gis_agent_harness.cli import main
from gis_agent_harness.improvement_catalog import (
    build_improvement_catalog,
    render_improvement_catalog_markdown,
)


def test_improvement_catalog_contains_large_offline_backlog() -> None:
    catalog = build_improvement_catalog()
    payload = catalog.to_dict()

    assert payload["total_available"] >= 900
    assert payload["returned_count"] == payload["total_available"]
    assert payload["summary"]["by_category"]["cli"] >= 50
    assert payload["summary"]["by_category"]["testing"] >= 50
    assert payload["summary"]["offline_only"] is True


def test_improvement_catalog_filters_by_category_priority_and_text() -> None:
    catalog = build_improvement_catalog(category="cli", min_priority="high", contains="output", limit=5)
    payload = catalog.to_dict()

    assert payload["filters"] == {
        "category": "cli",
        "min_priority": "high",
        "contains": "output",
        "limit": 5,
    }
    assert payload["total_available"] >= 5
    assert payload["returned_count"] == 5
    assert all(item["category"] == "cli" for item in payload["items"])
    assert all(item["priority"] in {"critical", "high"} for item in payload["items"])
    assert all("output" in json.dumps(item).lower() for item in payload["items"])


def test_improvement_catalog_markdown_renderer() -> None:
    catalog = build_improvement_catalog(category="security", limit=3)

    markdown = render_improvement_catalog_markdown(catalog)

    assert markdown.startswith("# GIS Agent Harness Improvement Catalog")
    assert "Total available:" in markdown
    assert "| ID | Category | Priority | Area | Title |" in markdown
    assert markdown.count("| security-") == 3


def test_improvement_catalog_cli_json_output_file(tmp_path: Path) -> None:
    output_file = tmp_path / "catalog" / "improvements.json"
    runner = CliRunner()

    result = runner.invoke(
        main,
        [
            "improvement-catalog",
            "--category",
            "testing",
            "--min-priority",
            "medium",
            "--limit",
            "7",
            "--output-file",
            str(output_file),
        ],
    )

    assert result.exit_code == 0
    assert output_file.exists()
    payload = json.loads(output_file.read_text(encoding="utf-8"))
    assert payload["returned_count"] == 7
    assert payload["total_available"] >= 7
    assert all(item["category"] == "testing" for item in payload["items"])


def test_improvement_catalog_cli_markdown() -> None:
    runner = CliRunner()

    result = runner.invoke(
        main,
        [
            "improvement-catalog",
            "--format",
            "markdown",
            "--category",
            "documentation",
            "--limit",
            "4",
        ],
    )

    assert result.exit_code == 0
    assert "# GIS Agent Harness Improvement Catalog" in result.output
    assert "documentation-" in result.output


def test_improvement_catalog_cli_import_does_not_load_heavy_gis_dependencies() -> None:
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
