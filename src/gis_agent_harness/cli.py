from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import click

from .config import HarnessConfig
from .errors import DataInspectionError


def _render_json(payload: object) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False)


def _emit_text(text: str, output_file: Path | None = None) -> None:
    if output_file is not None:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(text + ("\n" if not text.endswith("\n") else ""), encoding="utf-8")
    click.echo(text)


def _dump(payload: object, output_file: Path | None = None) -> None:
    _emit_text(_render_json(payload), output_file=output_file)


def _render_runs_table(rows: list[dict[str, object]]) -> str:
    headers = ["run_id", "status", "stage", "task_summary"]
    table_rows = []
    for row in rows:
        table_rows.append(
            {
                "run_id": str(row.get("run_id", "")),
                "status": str(row.get("status", "")),
                "stage": str(row.get("failed_stage", "")),
                "task_summary": str((row.get("task") or {}).get("task_summary", "")),
            }
        )

    widths = {header: len(header) for header in headers}
    for row in table_rows:
        for header in headers:
            widths[header] = max(widths[header], len(row[header]))

    def render_line(values: dict[str, str]) -> str:
        return "  ".join(values[header].ljust(widths[header]) for header in headers)

    header_row = {header: header for header in headers}
    separator_row = {header: "-" * widths[header] for header in headers}
    lines = [render_line(header_row), render_line(separator_row)]
    for row in table_rows:
        lines.append(render_line(row))
    return "\n".join(lines)


def _render_state_table(rows: list[dict[str, object]]) -> str:
    headers = ["run_id", "status", "stage", "summary"]
    table_rows = []
    for row in rows:
        table_rows.append(
            {
                "run_id": str(row.get("run_id", "")),
                "status": str(row.get("status", "")),
                "stage": str(row.get("stage", "")),
                "summary": str(row.get("summary", "")),
            }
        )

    widths = {header: len(header) for header in headers}
    for row in table_rows:
        for header in headers:
            widths[header] = max(widths[header], len(row[header]))

    def render_line(values: dict[str, str]) -> str:
        return "  ".join(values[header].ljust(widths[header]) for header in headers)

    header_row = {header: header for header in headers}
    separator_row = {header: "-" * widths[header] for header in headers}
    lines = [render_line(header_row), render_line(separator_row)]
    for row in table_rows:
        lines.append(render_line(row))
    return "\n".join(lines)


def _render_failure_files_table(payload: dict[str, object]) -> str:
    headers = ["run_id", "status", "stage", "log_json", "log_py", "failed_scripts"]
    row = {
        "run_id": str(payload.get("run_id", "")),
        "status": str(payload.get("status", "")),
        "stage": str(payload.get("failed_stage", "")),
        "log_json": str(len(payload.get("log_json_files", []))),
        "log_py": str(len(payload.get("log_py_files", []))),
        "failed_scripts": str(len(payload.get("failed_scripts", []))),
    }

    widths = {header: max(len(header), len(row[header])) for header in headers}

    def render_line(values: dict[str, str]) -> str:
        return "  ".join(values[header].ljust(widths[header]) for header in headers)

    header_row = {header: header for header in headers}
    separator_row = {header: "-" * widths[header] for header in headers}
    return "\n".join([render_line(header_row), render_line(separator_row), render_line(row)])


def _render_replay_table(payload: dict[str, object]) -> str:
    headers = ["run_id", "status", "stage", "task_summary", "suggested_fix"]
    row = {
        "run_id": str(payload.get("run_id", "")),
        "status": str(payload.get("status", "")),
        "stage": str(payload.get("failed_stage", "")),
        "task_summary": str((payload.get("task") or {}).get("task_summary", "")),
        "suggested_fix": str(payload.get("suggested_fix", "")),
    }

    widths = {header: max(len(header), len(row[header])) for header in headers}

    def render_line(values: dict[str, str]) -> str:
        return "  ".join(values[header].ljust(widths[header]) for header in headers)

    header_row = {header: header for header in headers}
    separator_row = {header: "-" * widths[header] for header in headers}
    return "\n".join([render_line(header_row), render_line(separator_row), render_line(row)])


def _render_index_text(payload: dict[str, object]) -> str:
    files = payload.get("files", {})
    lines = [
        f"run_id: {payload['run_id']}",
        f"output_dir: {payload['output_dir']}",
        f"summary: {payload['summary']}",
        f"suggested_fix: {payload.get('suggested_fix') or ''}",
        "files:",
    ]
    lines.extend(f"- {name}: {path}" for name, path in files.items())
    return "\n".join(lines)


def _render_adoption_report_text(payload: dict[str, object]) -> str:
    lines = [
        f"run_id: {payload.get('run_id', '')}",
        f"status: {payload.get('status', '')}",
        f"summary: {payload.get('summary', '')}",
        "source_data:",
    ]
    for dataset in payload.get("source_data", []):
        item = dataset if isinstance(dataset, dict) else {}
        lines.append(
            "- "
            + ", ".join(
                [
                    f"role={item.get('role', '')}",
                    f"path={item.get('path', '')}",
                    f"kind={item.get('kind', '')}",
                    f"crs={item.get('crs', '')}",
                    f"sha256={(item.get('hashes') or {}).get('sha256', '') if isinstance(item.get('hashes'), dict) else ''}",
                ]
            )
        )
    lines.append("crs_transformations:")
    for transform in payload.get("crs_transformations", []):
        item = transform if isinstance(transform, dict) else {}
        lines.append(f"- {item.get('source_crs', '')} -> {item.get('target_crs', '')}: {item.get('reason', '')}")
    lines.append("actions:")
    for action in payload.get("actions", []):
        item = action if isinstance(action, dict) else {}
        lines.append(f"- iter={item.get('iteration', '')}, action={item.get('action', '')}, output={item.get('output_vector_path', '')}")
    lines.append("lineage:")
    lineage = payload.get("lineage", {}) if isinstance(payload.get("lineage"), dict) else {}
    for node in lineage.get("nodes", []):
        item = node if isinstance(node, dict) else {}
        lines.append(
            f"- node {item.get('id', '')}: kind={item.get('kind', '')}, role={item.get('role', '')}, path={item.get('path', '')}, action={item.get('action', '')}"
        )
    for edge in lineage.get("edges", []):
        item = edge if isinstance(edge, dict) else {}
        lines.append(f"- edge {item.get('from', '')} -> {item.get('to', '')}: {item.get('relation', '')}")
    lines.append("omitted_steps:")
    for omitted in payload.get("omitted_steps", []):
        item = omitted if isinstance(omitted, dict) else {}
        lines.append(f"- {item.get('code', '')}: {item.get('reason', '')}")
    return "\n".join(lines)


def _render_templates_table(rows: list[dict[str, object]]) -> str:
    headers = ["template_id", "title", "fields"]
    normalized = [
        {
            "template_id": str(row.get("template_id", "")),
            "title": str(row.get("title", "")),
            "fields": ",".join(str(field.get("name")) for field in row.get("fields", [])),
        }
        for row in rows
    ]
    widths = {header: len(header) for header in headers}
    for row in normalized:
        for header in headers:
            widths[header] = max(widths[header], len(row[header]))

    def render_line(values: dict[str, str]) -> str:
        return "  ".join(values[header].ljust(widths[header]) for header in headers)

    lines = [
        render_line({header: header for header in headers}),
        render_line({header: "-" * widths[header] for header in headers}),
    ]
    lines.extend(render_line(row) for row in normalized)
    return "\n".join(lines)


def _resolve_latest_report_dir(reports_root: Path) -> Path | None:
    if not reports_root.exists():
        return None
    candidates = [
        path
        for path in reports_root.iterdir()
        if path.is_dir() and ((path / "index.json").exists() or (path / "index.txt").exists())
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime)


def _write_report_bundle(report_dir: Path, entries: dict[str, str]) -> dict[str, str]:
    report_dir.mkdir(parents=True, exist_ok=True)
    written: dict[str, str] = {}
    for name, content in entries.items():
        path = report_dir / name
        path.write_text(content + ("\n" if not content.endswith("\n") else ""), encoding="utf-8")
        written[name] = str(path)
    return written


def _load_runtime_config(
    *,
    state_file: Path | None = None,
    run_root: Path | None = None,
    use_mock: bool | None = None,
    max_iterations: int | None = None,
) -> HarnessConfig:
    config = HarnessConfig.from_env()
    if state_file is not None:
        config.state_file = state_file
    if run_root is not None:
        config.run_root = run_root
        config.sandbox_write_root = run_root / "artifacts"
        config.telemetry_file = run_root / "telemetry.jsonl"
    if use_mock is not None:
        config.use_mock = use_mock
        if use_mock:
            config.provider = "mock"
    if max_iterations is not None:
        config.max_iterations = max_iterations
    return config


def _render_rerun_command(task_payload: dict[str, Any]) -> str:
    command_parts = ["python3", "-m", "gis_agent_harness.cli", "run-task"]
    if task_payload.get("task_summary"):
        command_parts.extend(["--task-summary", task_payload["task_summary"]])
    if task_payload.get("vector_path"):
        command_parts.extend(["--vector", task_payload["vector_path"]])
    if task_payload.get("raster_path"):
        command_parts.extend(["--raster", task_payload["raster_path"]])
    if task_payload.get("source_crs"):
        command_parts.extend(["--source-crs", task_payload["source_crs"]])
    return " ".join(json.dumps(part, ensure_ascii=False) for part in command_parts)


@click.group()
def main() -> None:
    """GIS Agent Harness CLI."""


@main.command("inspect-vector")
@click.argument("path", type=click.Path(path_type=Path))
@click.option("--sample-size", default=3, show_default=True, type=int)
def inspect_vector_command(path: Path, sample_size: int) -> None:
    """Inspect vector dataset metadata."""
    from .spatial_tools import inspect_vector

    try:
        result = inspect_vector(path, sample_size=sample_size)
    except DataInspectionError as exc:
        raise click.ClickException(str(exc)) from exc
    _dump(result.to_dict())


@main.command("inspect-raster")
@click.argument("path", type=click.Path(path_type=Path))
def inspect_raster_command(path: Path) -> None:
    """Inspect raster dataset metadata."""
    from .spatial_tools import inspect_raster

    try:
        result = inspect_raster(path)
    except DataInspectionError as exc:
        raise click.ClickException(str(exc)) from exc
    _dump(result.to_dict())


@main.command("spatial-map")
@click.argument("root", type=click.Path(path_type=Path), default=Path("."))
@click.option("--max-datasets", default=50, show_default=True, type=int)
@click.option("--max-schema-fields", default=12, show_default=True, type=int)
@click.option("--exclude-dir", multiple=True, help="Additional directory name to skip while scanning.")
@click.option("--dataset", "dataset_path", type=click.Path(path_type=Path), default=None, help="Return detail for one dataset relative to the root.")
@click.option("--output-file", type=click.Path(path_type=Path), default=None, help="Optional path to write the map JSON.")
def spatial_map_command(
    root: Path,
    max_datasets: int,
    max_schema_fields: int,
    exclude_dir: tuple[str, ...],
    dataset_path: Path | None,
    output_file: Path | None,
) -> None:
    """Build a compressed spatial repo map without reading full geometries."""
    from .spatial_context import build_spatial_repo_map, describe_spatial_dataset

    try:
        result = (
            describe_spatial_dataset(root, dataset_path)
            if dataset_path is not None
            else build_spatial_repo_map(
                root,
                max_datasets=max_datasets,
                max_schema_fields=max_schema_fields,
                exclude_dirs=set(exclude_dir),
            )
        )
    except Exception as exc:
        raise click.ClickException(str(exc)) from exc
    _dump(result.to_dict(), output_file=output_file)


@main.command("qgis-run")
@click.argument("algorithm")
@click.option("--payload-file", type=click.Path(path_type=Path), default=None, help="JSON object passed to qgis_process stdin.")
@click.option("--payload-json", default=None, help="Inline JSON object passed to qgis_process stdin.")
@click.option("--qgis-process-path", default="qgis_process", show_default=True)
@click.option("--timeout", "timeout_seconds", default=120, show_default=True, type=int)
@click.option("--dry-run/--execute", default=True, show_default=True, help="Render the qgis_process request or execute it.")
@click.option("--confirm", is_flag=True, help="Required with --execute before running qgis_process locally.")
@click.option("--output-file", type=click.Path(path_type=Path), default=None, help="Optional path to write the result JSON.")
def qgis_run_command(
    algorithm: str,
    payload_file: Path | None,
    payload_json: str | None,
    qgis_process_path: str,
    timeout_seconds: int,
    dry_run: bool,
    confirm: bool,
    output_file: Path | None,
) -> None:
    """Run or preview a qgis_process algorithm using a JSON payload."""
    from .qgis_process import QGISProcessError, QGISProcessRequest, load_payload, run_qgis_process

    try:
        config = HarnessConfig.from_env()
        parameters = load_payload(payload_file, payload_json)
        request = QGISProcessRequest(
            algorithm=algorithm,
            parameters=parameters,
            qgis_process_path=qgis_process_path,
        )
        result = run_qgis_process(
            request,
            dry_run=dry_run,
            timeout_seconds=timeout_seconds,
            confirmed=(confirm or not config.qgis_require_confirm),
        )
    except QGISProcessError as exc:
        raise click.ClickException(str(exc)) from exc
    _dump(result.to_dict(), output_file=output_file)
    if not result.success:
        raise click.exceptions.Exit(1)


@main.command("mcp-tools")
@click.option("--domain", default=None, help="Optional progressive-disclosure domain filter.")
def mcp_tools_command(domain: str | None) -> None:
    """Render the local MCP-style GIS tool manifest."""
    from .mcp_registry import build_mcp_manifest

    _dump(build_mcp_manifest(domain=domain).to_dict())


@main.command("mcp-call")
@click.argument("tool_name")
@click.option("--params-json", default="{}", show_default=True, help="Tool parameters JSON object.")
def mcp_call_command(tool_name: str, params_json: str) -> None:
    """Call a local MCP-style tool through the harness dispatcher."""
    from .mcp_runtime import call_mcp_tool

    try:
        payload = json.loads(params_json)
    except json.JSONDecodeError as exc:
        raise click.ClickException(f"Invalid --params-json: {exc}") from exc
    if not isinstance(payload, dict):
        raise click.ClickException("--params-json must decode to a JSON object.")
    result = call_mcp_tool(tool_name, payload)
    _dump(result.to_dict())
    if not result.success:
        raise click.exceptions.Exit(1)


@main.command("align-params")
@click.option("--params-json", required=True, help="Inline JSON object of spatial tool parameters.")
def align_params_command(params_json: str) -> None:
    """Normalize common CRS, bbox, and numeric GIS parameters before execution."""
    from .parameter_alignment import align_parameters

    try:
        payload = json.loads(params_json)
    except json.JSONDecodeError as exc:
        raise click.ClickException(f"Invalid --params-json: {exc}") from exc
    if not isinstance(payload, dict):
        raise click.ClickException("--params-json must decode to a JSON object.")
    _dump(align_parameters(payload).to_dict())


@main.command("capture-artifact")
@click.argument("path", type=click.Path(path_type=Path))
@click.option("--output-dir", type=click.Path(path_type=Path), default=None)
def capture_artifact_command(path: Path, output_dir: Path | None) -> None:
    """Capture a map/image artifact with hash and compact base64 thumbnail."""
    from .visual_artifacts import capture_visual_artifact

    try:
        artifact = capture_visual_artifact(path, output_dir=output_dir)
    except FileNotFoundError as exc:
        raise click.ClickException(str(exc)) from exc
    _dump(artifact.to_dict())


@main.command("judge-map")
@click.argument("path", type=click.Path(path_type=Path))
@click.option("--criteria-json", default="{}", show_default=True, help="Visual review criteria JSON.")
@click.option("--output-dir", type=click.Path(path_type=Path), default=None)
def judge_map_command(path: Path, criteria_json: str, output_dir: Path | None) -> None:
    """Run a deterministic local map-product review over captured artifact metadata."""
    from .visual_artifacts import capture_visual_artifact
    from .visual_judge import judge_map_product

    try:
        criteria = json.loads(criteria_json)
    except json.JSONDecodeError as exc:
        raise click.ClickException(f"Invalid --criteria-json: {exc}") from exc
    if not isinstance(criteria, dict):
        raise click.ClickException("--criteria-json must decode to a JSON object.")
    artifact = capture_visual_artifact(path, output_dir=output_dir)
    _dump(judge_map_product(artifact, criteria).to_dict())


def _parse_bbox(value: str) -> list[float]:
    try:
        bbox = [float(item.strip()) for item in value.split(",")]
    except ValueError as exc:
        raise click.ClickException("--bbox must be four comma-separated numbers.") from exc
    if len(bbox) != 4:
        raise click.ClickException("--bbox must contain exactly four comma-separated numbers.")
    return bbox


@main.command("stac-plan")
@click.option("--collection", "collections", multiple=True, required=True, help="STAC collection id. Repeatable.")
@click.option("--bbox", required=True, help="minx,miny,maxx,maxy")
@click.option("--datetime", "datetime_range", required=True, help="STAC datetime range.")
@click.option("--max-cloud-cover", type=float, default=None)
@click.option("--endpoint", default="https://planetarycomputer.microsoft.com/api/stac/v1/search", show_default=True)
def stac_plan_command(
    collections: tuple[str, ...],
    bbox: str,
    datetime_range: str,
    max_cloud_cover: float | None,
    endpoint: str,
) -> None:
    """Build a local dry-run STAC discovery request."""
    from .stac_discovery import build_stac_query_plan

    _dump(
        build_stac_query_plan(
            collections=list(collections),
            bbox=_parse_bbox(bbox),
            datetime_range=datetime_range,
            max_cloud_cover=max_cloud_cover,
            endpoint=endpoint,
        ).to_dict()
    )


@main.command("route-resource")
@click.option("--script-file", type=click.Path(path_type=Path), default=None)
@click.option("--script-text", default=None)
def route_resource_command(script_file: Path | None, script_text: str | None) -> None:
    """Classify generated code into CPU/GPU container tracks."""
    from .resource_router import route_code

    if script_file is None and script_text is None:
        raise click.ClickException("Provide either --script-file or --script-text.")
    if script_file is not None and script_text is not None:
        raise click.ClickException("Use either --script-file or --script-text, not both.")
    text = script_file.read_text(encoding="utf-8") if script_file is not None else str(script_text)
    _dump(route_code(text).to_dict())


@main.command("compact-failures")
@click.option("--history-json", required=True, help="JSON array of previous action attempts.")
@click.option("--max-repeats", default=3, show_default=True, type=int)
def compact_failures_command(history_json: str, max_repeats: int) -> None:
    """Detect repeated failed actions and render a compact replanning warning."""
    from .context_compaction import compact_failure_history

    try:
        history = json.loads(history_json)
    except json.JSONDecodeError as exc:
        raise click.ClickException(f"Invalid --history-json: {exc}") from exc
    if not isinstance(history, list) or not all(isinstance(item, dict) for item in history):
        raise click.ClickException("--history-json must decode to an array of objects.")
    _dump(compact_failure_history(history, max_repeats=max_repeats).to_dict())


@main.command("faas-manifest")
@click.option("--function-name", required=True)
@click.option("--image", required=True)
@click.option("--handler", required=True)
@click.option("--input-asset", "input_assets", multiple=True)
@click.option("--script-file", type=click.Path(path_type=Path), default=None)
@click.option("--script-text", default="")
def faas_manifest_command(
    function_name: str,
    image: str,
    handler: str,
    input_assets: tuple[str, ...],
    script_file: Path | None,
    script_text: str,
) -> None:
    """Render a local-first FaaS deployment manifest without deploying it."""
    from .faas_planner import build_faas_manifest
    from .resource_router import route_code

    text = script_file.read_text(encoding="utf-8") if script_file is not None else script_text
    _dump(
        build_faas_manifest(
            function_name=function_name,
            image=image,
            handler=handler,
            input_assets=list(input_assets),
            resource_route=route_code(text),
        )
    )


@main.command("qgis-plugin-manifest")
@click.option("--plugin-name", default="GISAgentMCPBridge", show_default=True)
def qgis_plugin_manifest_command(plugin_name: str) -> None:
    """Render the desktop QGIS MCP bridge plugin manifest."""
    from .qgis_plugin import build_qgis_plugin_manifest

    _dump(build_qgis_plugin_manifest(plugin_name=plugin_name))


@main.command("cog-viewer")
@click.option("--output-html", type=click.Path(path_type=Path), required=True)
@click.option("--cog-url", required=True)
@click.option("--title", default="COG Review", show_default=True)
def cog_viewer_command(output_html: Path, cog_url: str, title: str) -> None:
    """Create a static browser-side COG review HTML manifest."""
    from .cog_viewer import build_cog_viewer

    path = build_cog_viewer(output_html=output_html, cog_url=cog_url, title=title)
    _dump({"output_html": str(path), "exists": path.exists()})


@main.command("benchmark-manifest")
@click.option("--junit-file", type=click.Path(path_type=Path), default=None)
def benchmark_manifest_command(junit_file: Path | None) -> None:
    """Render the local GeoAgentBench/GeoBenchX/GIS-Bench manifest."""
    from .benchmarking import build_benchmark_manifest
    from .pipeline_reporting import PipelineCheck, render_junit_xml

    manifest = build_benchmark_manifest()
    checks = [
        PipelineCheck(name="GeoAgentBench manifest", passed="GeoAgentBench" in manifest["suites"]),
        PipelineCheck(name="GeoBenchX manifest", passed="GeoBenchX" in manifest["suites"]),
        PipelineCheck(name="GIS-Bench manifest", passed="GIS-Bench" in manifest["suites"]),
    ]
    if junit_file is not None:
        junit_file.parent.mkdir(parents=True, exist_ok=True)
        junit_file.write_text(render_junit_xml("geoai-benchmark-manifest", checks), encoding="utf-8")
    _dump({**manifest, "junit_file": str(junit_file) if junit_file is not None else None})


@main.command("benchmark-run")
def benchmark_run_command() -> None:
    """Run local benchmark-manifest sanity checks."""
    from .benchmarking import run_benchmark_checks

    payload = run_benchmark_checks()
    _dump(payload)
    if payload["status"] != "succeeded":
        raise click.exceptions.Exit(1)


@main.command("method-review")
@click.option("--analysis-json", required=True, help="JSON object describing the spatial method.")
@click.option("--max-rounds", default=4, show_default=True, type=int)
def method_review_command(analysis_json: str, max_rounds: int) -> None:
    """Run a deterministic adversarial GIS methodology review."""
    from .adversarial_review import run_method_review

    try:
        analysis = json.loads(analysis_json)
    except json.JSONDecodeError as exc:
        raise click.ClickException(f"Invalid --analysis-json: {exc}") from exc
    if not isinstance(analysis, dict):
        raise click.ClickException("--analysis-json must decode to a JSON object.")
    _dump(run_method_review(analysis, max_rounds=max_rounds))


@main.command("explain-exception")
@click.argument("message")
def explain_exception_command(message: str) -> None:
    """Translate common GDAL/GEOS/OGR failures into repair guidance."""
    from .geo_exception_parser import explain_geospatial_exception

    _dump(explain_geospatial_exception(message).to_dict())


@main.command("requirement-matrix")
def requirement_matrix_command() -> None:
    """Render blueprint requirement implementation evidence."""
    from .requirement_matrix import build_requirement_matrix

    _dump(build_requirement_matrix())


@main.command("health-report")
@click.option("--root", type=click.Path(path_type=Path), default=Path("."), show_default=True)
@click.option("--category", default=None, help="Only include checks from one category.")
@click.option("--format", "output_format", type=click.Choice(["json", "markdown"]), default="json", show_default=True)
@click.option("--output-file", type=click.Path(path_type=Path), default=None, help="Optional path to write the rendered report.")
def health_report_command(
    root: Path,
    category: str | None,
    output_format: str,
    output_file: Path | None,
) -> None:
    """Render a local project health report with 50+ implementation checks."""
    from .health_report import build_health_report, render_health_report_markdown

    report = build_health_report(root, category=category)
    if output_format == "markdown":
        _emit_text(render_health_report_markdown(report), output_file=output_file)
        return
    _dump(report.to_dict(), output_file=output_file)


@main.command("project-metrics")
@click.option("--root", type=click.Path(path_type=Path), default=Path("."), show_default=True)
@click.option("--target-commits", type=click.IntRange(min=0), default=None, help="Optional commit-count target.")
@click.option("--target-python-lines", type=click.IntRange(min=0), default=None, help="Optional tracked Python line target.")
@click.option("--top-files", type=click.IntRange(min=0), default=10, show_default=True, help="Number of largest tracked Python files to include.")
@click.option("--format", "output_format", type=click.Choice(["json", "markdown"]), default="json", show_default=True)
@click.option("--fail-on-unmet-targets", is_flag=True, help="Exit with status 1 when any configured target is unmet.")
@click.option("--output-file", type=click.Path(path_type=Path), default=None, help="Optional path to write the rendered metrics.")
def project_metrics_command(
    root: Path,
    target_commits: int | None,
    target_python_lines: int | None,
    top_files: int,
    output_format: str,
    fail_on_unmet_targets: bool,
    output_file: Path | None,
) -> None:
    """Render local Git and tracked-code metrics for progress audits."""
    from .project_metrics import build_project_metrics, render_project_metrics_markdown

    metrics = build_project_metrics(
        root,
        target_commits=target_commits,
        target_python_lines=target_python_lines,
        top_files_limit=top_files,
    )
    payload = metrics.to_dict()
    target_values = payload.get("targets", {})
    has_unmet_target = any(
        isinstance(target, dict) and target.get("met") is False
        for target in (target_values.values() if isinstance(target_values, dict) else [])
    )
    if output_format == "markdown":
        _emit_text(render_project_metrics_markdown(metrics), output_file=output_file)
        if fail_on_unmet_targets and has_unmet_target:
            raise click.exceptions.Exit(1)
        return
    _dump(payload, output_file=output_file)
    if fail_on_unmet_targets and has_unmet_target:
        raise click.exceptions.Exit(1)


@main.command("improvement-catalog")
@click.option("--category", default=None, help="Only include improvement items from one category.")
@click.option(
    "--min-priority",
    type=click.Choice(["low", "medium", "high", "critical"]),
    default=None,
    help="Only include items at or above this priority.",
)
@click.option("--contains", default=None, help="Case-insensitive text filter over item fields.")
@click.option("--limit", default=None, type=int, help="Maximum number of items to return after filtering.")
@click.option("--format", "output_format", type=click.Choice(["json", "markdown"]), default="json", show_default=True)
@click.option("--output-file", type=click.Path(path_type=Path), default=None, help="Optional path to write the rendered catalog.")
def improvement_catalog_command(
    category: str | None,
    min_priority: str | None,
    contains: str | None,
    limit: int | None,
    output_format: str,
    output_file: Path | None,
) -> None:
    """Render the offline GIS harness improvement catalog."""
    from .improvement_catalog import build_improvement_catalog, render_improvement_catalog_markdown

    try:
        catalog = build_improvement_catalog(
            category=category,
            min_priority=min_priority,
            contains=contains,
            limit=limit,
        )
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    if output_format == "markdown":
        _emit_text(render_improvement_catalog_markdown(catalog), output_file=output_file)
        return
    _dump(catalog.to_dict(), output_file=output_file)


@main.command("narrative-report")
@click.option("--adoption-json-file", type=click.Path(path_type=Path), required=True)
@click.option("--output-file", type=click.Path(path_type=Path), required=True)
def narrative_report_command(adoption_json_file: Path, output_file: Path) -> None:
    """Build a Markdown provenance narrative from an adoption-report JSON file."""
    from .narrative_report import build_narrative_report

    try:
        payload = json.loads(adoption_json_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise click.ClickException(f"Invalid adoption report JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise click.ClickException("Adoption report JSON must decode to an object.")
    _dump(build_narrative_report(payload, output_path=output_file))


@main.command("run-task")
@click.option("--task-summary", required=True, help="Short task description.")
@click.option("--vector", "vector_path", required=True, type=click.Path(path_type=Path))
@click.option("--raster", "raster_path", type=click.Path(path_type=Path))
@click.option("--source-crs", help="Declare the source CRS when vector metadata is missing.")
@click.option("--max-iterations", default=None, type=int, help="Override the configured retry budget.")
@click.option("--mock/--live", "use_mock", default=None, help="Use mock or live LiteLLM routing.")
@click.option("--run-root", type=click.Path(path_type=Path), default=None)
@click.option("--state-file", type=click.Path(path_type=Path), default=None)
def run_task_command(
    task_summary: str,
    vector_path: Path,
    raster_path: Path | None,
    source_crs: str | None,
    max_iterations: int | None,
    use_mock: bool | None,
    run_root: Path | None,
    state_file: Path | None,
) -> None:
    """Run the guarded mock-first repair loop."""
    from .agent_loop import AgentTask
    from .goal_runner import run_agent_task

    config = _load_runtime_config(
        state_file=state_file,
        run_root=run_root,
        use_mock=use_mock,
        max_iterations=max_iterations,
    )
    task = AgentTask(
        task_summary=task_summary,
        vector_path=str(vector_path),
        raster_path=str(raster_path) if raster_path else None,
        source_crs=source_crs,
        max_iterations=config.max_iterations,
    )
    result = run_agent_task(task, config)
    _dump(result.to_dict())
    if result.status != "succeeded":
        raise click.exceptions.Exit(1)


@main.group("templates")
def templates_group() -> None:
    """Template registry helpers."""


@templates_group.command("list")
@click.option("--format", "output_format", type=click.Choice(["json", "table"]), default="json", show_default=True)
def templates_list_command(output_format: str) -> None:
    """List built-in GIS goal templates."""
    from .task_templates import TemplateRegistry

    templates = [template.to_dict() for template in TemplateRegistry().list()]
    if output_format == "table":
        _emit_text(_render_templates_table(templates))
        return
    _dump(templates)


@main.group("goal")
def goal_group() -> None:
    """Goal-oriented wrappers around AgentTask."""


@goal_group.command("run")
@click.option("--template", "template_id", required=False, default=None, help="Built-in goal template id.")
@click.option("--plan-file", type=click.Path(path_type=Path), default=None, help="Optional YAML/Markdown execution plan.")
@click.option("--vector", type=click.Path(path_type=Path), default=None)
@click.option("--raster", type=click.Path(path_type=Path), default=None)
@click.option("--source-crs", default=None)
@click.option("--task-summary", default=None, help="Optional override for the rendered task summary.")
@click.option("--max-iterations", default=None, type=int)
@click.option("--mock/--live", "use_mock", default=None)
@click.option("--dry-run", is_flag=True, help="Render the template into an AgentTask without executing it.")
@click.option("--run-root", type=click.Path(path_type=Path), default=None)
@click.option("--state-file", type=click.Path(path_type=Path), default=None)
def goal_run_command(
    template_id: str | None,
    plan_file: Path | None,
    vector: Path | None,
    raster: Path | None,
    source_crs: str | None,
    task_summary: str | None,
    max_iterations: int | None,
    use_mock: bool | None,
    dry_run: bool,
    run_root: Path | None,
    state_file: Path | None,
) -> None:
    """Render a template into AgentTask and run the existing agent loop."""
    from .goal_runner import GoalRunner, GoalSpec

    config = _load_runtime_config(
        state_file=state_file,
        run_root=run_root,
        use_mock=use_mock,
        max_iterations=max_iterations,
    )
    inputs = {
        "vector": str(vector) if vector else None,
        "raster": str(raster) if raster else None,
        "source_crs": source_crs,
    }
    spec = GoalSpec(
        template_id=template_id,
        inputs={key: value for key, value in inputs.items() if value is not None},
        task_summary=task_summary,
        max_iterations=max_iterations,
        use_mock=use_mock,
        run_root=run_root,
        state_file=state_file,
        plan_file=plan_file,
    )
    runner = GoalRunner(config)
    try:
        preview = runner.preview(spec)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    except KeyError as exc:
        raise click.ClickException(str(exc)) from exc
    if dry_run:
        _dump(preview)
        return
    result = runner.run(spec)
    _dump(result.to_dict())
    if result.status != "succeeded":
        raise click.exceptions.Exit(1)


@main.group("config")
def config_group() -> None:
    """Configuration helpers."""


@config_group.command("doctor")
@click.option("--mock/--live", "use_mock", default=None)
@click.option("--run-root", type=click.Path(path_type=Path), default=None)
@click.option("--state-file", type=click.Path(path_type=Path), default=None)
def config_doctor_command(use_mock: bool | None, run_root: Path | None, state_file: Path | None) -> None:
    """Inspect merged config and provider profile readiness."""
    from .auth_config import doctor_config

    config = _load_runtime_config(state_file=state_file, run_root=run_root, use_mock=use_mock)
    _dump(doctor_config(config))


@main.command("tui")
@click.option("--mock/--live", "use_mock", default=None)
@click.option("--run-root", type=click.Path(path_type=Path), default=None)
@click.option("--state-file", type=click.Path(path_type=Path), default=None)
def tui_command(use_mock: bool | None, run_root: Path | None, state_file: Path | None) -> None:
    """Launch the Textual TUI."""
    from .tui import GISAgentApp

    config = _load_runtime_config(state_file=state_file, run_root=run_root, use_mock=use_mock)
    GISAgentApp(config=config).run()


@main.command("show-state")
@click.option("--limit", default=5, show_default=True, type=int)
@click.option("--format", "output_format", type=click.Choice(["json", "markdown", "table"]), default="json", show_default=True)
@click.option("--run-id", default=None, help="Filter JSON output to a specific run id.")
@click.option("--status", default=None, help="Filter JSON output by snapshot status.")
@click.option("--stage", default=None, help="Filter JSON output by snapshot stage.")
@click.option("--failed-only", is_flag=True, help="Only include failed snapshots in JSON output.")
@click.option("--output-file", type=click.Path(path_type=Path), default=None, help="Optional path to write the rendered output.")
@click.option("--state-file", type=click.Path(path_type=Path), default=None)
@click.option("--run-root", type=click.Path(path_type=Path), default=None)
def show_state_command(
    limit: int,
    output_format: str,
    run_id: str | None,
    status: str | None,
    stage: str | None,
    failed_only: bool,
    output_file: Path | None,
    state_file: Path | None,
    run_root: Path | None,
) -> None:
    """Show recent state snapshots."""
    from .state_store import StateStore

    config = _load_runtime_config(state_file=state_file, run_root=run_root)
    store = StateStore(config.state_file, config.run_root)
    if output_format == "markdown" and any(value is not None for value in (run_id, status, stage)) or (
        output_format == "markdown" and failed_only
    ):
        raise click.ClickException("Filtering options are only supported with --format json or --format table.")
    if output_format == "markdown":
        _emit_text(store.render_markdown(), output_file=output_file)
        return
    rows = store.recent(limit=limit, run_id=run_id, status=status, stage=stage, failed_only=failed_only)
    if output_format == "table":
        _emit_text(_render_state_table(rows), output_file=output_file)
        return
    _emit_text(_render_json(rows), output_file=output_file)


@main.command("show-telemetry")
@click.option("--run-root", type=click.Path(path_type=Path), default=None)
@click.option("--run-id", default=None, help="Filter telemetry events to a specific run id.")
@click.option("--event-type", default=None, help="Filter telemetry events to a specific event type.")
@click.option("--summary", is_flag=True, help="Render aggregated event counts instead of raw events.")
@click.option("--output-file", type=click.Path(path_type=Path), default=None, help="Optional path to write the rendered output.")
def show_telemetry_command(
    run_root: Path | None,
    run_id: str | None,
    event_type: str | None,
    summary: bool,
    output_file: Path | None,
) -> None:
    """Show the local telemetry event journal."""
    from .telemetry import load_telemetry_events, summarize_telemetry

    config = _load_runtime_config(run_root=run_root)
    payload = (
        summarize_telemetry(config.telemetry_file, run_id=run_id, event_type=event_type)
        if summary
        else load_telemetry_events(config.telemetry_file, run_id=run_id, event_type=event_type)
    )
    _dump(payload, output_file=output_file)


@main.command("list-runs")
@click.option("--limit", default=20, show_default=True, type=int)
@click.option("--failed-only", is_flag=True, help="Only include failed runs.")
@click.option("--status", default=None, help="Filter runs by terminal status, for example failed or succeeded.")
@click.option("--stage", default=None, help="Filter runs by terminal stage, for example stop or complete.")
@click.option("--contains", default=None, help="Filter by run id or task summary substring.")
@click.option("--format", "output_format", type=click.Choice(["json", "table"]), default="json", show_default=True)
@click.option("--output-file", type=click.Path(path_type=Path), default=None, help="Optional path to write the rendered output.")
@click.option("--state-file", type=click.Path(path_type=Path), default=None)
@click.option("--run-root", type=click.Path(path_type=Path), default=None)
def list_runs_command(
    limit: int,
    failed_only: bool,
    status: str | None,
    stage: str | None,
    contains: str | None,
    output_format: str,
    output_file: Path | None,
    state_file: Path | None,
    run_root: Path | None,
) -> None:
    """List recent runs as compact JSON summaries."""
    from .state_store import StateStore

    config = _load_runtime_config(state_file=state_file, run_root=run_root)
    store = StateStore(config.state_file, config.run_root)
    payload = store.query_runs(limit=limit, failed_only=failed_only, status=status, stage=stage, contains=contains)
    if output_format == "table":
        _emit_text(_render_runs_table(payload), output_file=output_file)
        return
    _dump(payload, output_file=output_file)


@main.command("resume-hint")
@click.option("--run-id", default=None, help="Show the summary for a specific run id instead of the latest failed run.")
@click.option("--state-file", type=click.Path(path_type=Path), default=None)
@click.option("--run-root", type=click.Path(path_type=Path), default=None)
def resume_hint_command(run_id: str | None, state_file: Path | None, run_root: Path | None) -> None:
    """Show a compact summary of the latest failed run."""
    from .state_store import StateStore

    config = _load_runtime_config(state_file=state_file, run_root=run_root)
    store = StateStore(config.state_file, config.run_root)
    payload = store.run_summary(run_id) if run_id is not None else store.latest_failed_run_summary()
    if payload is None:
        raise click.ClickException("No matching run snapshots are available.")
    _dump(payload)


@main.command("show-failure-files")
@click.option("--run-id", default=None, help="Show failure files for a specific run id instead of the latest failed run.")
@click.option("--format", "output_format", type=click.Choice(["json", "table"]), default="json", show_default=True)
@click.option("--output-file", type=click.Path(path_type=Path), default=None, help="Optional path to write the rendered output.")
@click.option("--state-file", type=click.Path(path_type=Path), default=None)
@click.option("--run-root", type=click.Path(path_type=Path), default=None)
def show_failure_files_command(
    run_id: str | None,
    output_format: str,
    output_file: Path | None,
    state_file: Path | None,
    run_root: Path | None,
) -> None:
    """Show log and failed-script paths for the latest failed run."""
    from .state_store import StateStore

    config = _load_runtime_config(state_file=state_file, run_root=run_root)
    store = StateStore(config.state_file, config.run_root)
    if run_id is not None:
        summary = store.run_summary(run_id)
        if summary is None:
            payload = None
        else:
            log_dir = Path(config.run_root) / "logs" / run_id
            failed_dir = Path(config.run_root) / "failed"
            payload = {
                **summary,
                "log_dir": str(log_dir),
                "log_json_files": sorted(str(path) for path in log_dir.glob("*.json")) if log_dir.exists() else [],
                "log_py_files": sorted(str(path) for path in log_dir.glob("*.py")) if log_dir.exists() else [],
                "failed_scripts": (
                    sorted(str(path) for path in failed_dir.glob(f"{run_id}-*.py")) if failed_dir.exists() else []
                ),
            }
    else:
        payload = store.latest_failed_run_files()
    if payload is None:
        raise click.ClickException("No matching run snapshots are available.")
    if output_format == "table":
        _emit_text(_render_failure_files_table(payload), output_file=output_file)
        return
    _dump(payload, output_file=output_file)


@main.command("show-replay")
@click.option("--run-id", default=None, help="Show the rerun command for a specific run id instead of the latest failed run.")
@click.option("--format", "output_format", type=click.Choice(["json", "table"]), default="json", show_default=True)
@click.option("--output-file", type=click.Path(path_type=Path), default=None, help="Optional path to write the rendered output.")
@click.option("--state-file", type=click.Path(path_type=Path), default=None)
@click.option("--run-root", type=click.Path(path_type=Path), default=None)
def show_replay_command(
    run_id: str | None,
    output_format: str,
    output_file: Path | None,
    state_file: Path | None,
    run_root: Path | None,
) -> None:
    """Show a suggested rerun command for the latest failed run."""
    from .state_store import StateStore

    config = _load_runtime_config(state_file=state_file, run_root=run_root)
    store = StateStore(config.state_file, config.run_root)
    if run_id is not None:
        summary = store.run_summary(run_id)
        task = store.task_for_run(run_id)
        if summary is None or task is None:
            payload = None
        else:
            payload = {
                **summary,
                "rerun_command": _render_rerun_command(task),
                "suggested_fix": summary.get("next_step_hint"),
            }
    else:
        payload = store.latest_failed_run_replay()
    if payload is None:
        raise click.ClickException("No matching run snapshots are available.")
    if output_format == "table":
        _emit_text(_render_replay_table(payload), output_file=output_file)
        return
    _dump(payload, output_file=output_file)


@main.command("adoption-report")
@click.argument("run_id", required=False)
@click.option("--latest", is_flag=True, help="Use the most recent run when RUN_ID is omitted.")
@click.option("--format", "output_format", type=click.Choice(["json", "text"]), default="json", show_default=True)
@click.option("--output-file", type=click.Path(path_type=Path), default=None, help="Optional path to write the report.")
@click.option("--state-file", type=click.Path(path_type=Path), default=None)
@click.option("--run-root", type=click.Path(path_type=Path), default=None)
def adoption_report_command(
    run_id: str | None,
    latest: bool,
    output_format: str,
    output_file: Path | None,
    state_file: Path | None,
    run_root: Path | None,
) -> None:
    """Export a per-run adoption report with data hashes and CRS decisions."""
    from .state_store import StateStore

    if latest and run_id is not None:
        raise click.ClickException("Use either RUN_ID or --latest, not both.")
    config = _load_runtime_config(state_file=state_file, run_root=run_root)
    store = StateStore(config.state_file, config.run_root)
    selected_run_id = run_id
    if selected_run_id is None:
        rows = store.query_runs(limit=1)
        if rows:
            selected_run_id = str(rows[0]["run_id"])
    if selected_run_id is None:
        raise click.ClickException("No run id was provided and no runs are available.")

    payload = store.adoption_report(selected_run_id)
    if payload is None:
        raise click.ClickException("No matching run snapshots are available.")
    if output_format == "text":
        _emit_text(_render_adoption_report_text(payload), output_file=output_file)
        return
    _dump(payload, output_file=output_file)


@main.command("show-report")
@click.option("--report-dir", type=click.Path(path_type=Path), default=None, help="Read a specific exported report bundle directory.")
@click.option("--latest", is_flag=True, help="Read the most recent bundle under the reports root.")
@click.option("--reports-root", type=click.Path(path_type=Path), default=Path("reports"), show_default=True)
@click.option(
    "--section",
    type=click.Choice(["index", "summary", "state", "failure-files", "replay", "adoption"]),
    default="index",
    show_default=True,
)
@click.option("--format", "output_format", type=click.Choice(["json", "text"]), default="text", show_default=True)
@click.option("--output-file", type=click.Path(path_type=Path), default=None, help="Optional path to write the rendered output.")
def show_report_command(
    report_dir: Path | None,
    latest: bool,
    reports_root: Path,
    section: str,
    output_format: str,
    output_file: Path | None,
) -> None:
    """Show a previously exported local report bundle."""
    if report_dir is not None and latest:
        raise click.ClickException("Use either --report-dir or --latest, not both.")

    resolved_dir = report_dir
    if resolved_dir is None:
        resolved_dir = _resolve_latest_report_dir(reports_root)
        if resolved_dir is None:
            raise click.ClickException("No exported report bundles are available.")
    if not resolved_dir.exists() or not resolved_dir.is_dir():
        raise click.ClickException("Report directory does not exist.")

    filenames = {
        "index": {"json": "index.json", "text": "index.txt"},
        "summary": {"json": "summary.json", "text": "summary.txt"},
        "state": {"json": "state.json", "text": "state.txt"},
        "failure-files": {"json": "failure-files.json", "text": "failure-files.txt"},
        "replay": {"json": "replay.json", "text": "replay.txt"},
        "adoption": {"json": "adoption.json", "text": "adoption.txt"},
    }
    artifact_path = resolved_dir / filenames[section][output_format]
    if not artifact_path.exists():
        raise click.ClickException(f"Report section is not available: {section} ({output_format}).")
    _emit_text(artifact_path.read_text(encoding="utf-8").rstrip("\n"), output_file=output_file)


@main.command("replay-last")
@click.option("--run-id", default=None, help="Replay a specific run id instead of the latest failed run.")
@click.option("--state-file", type=click.Path(path_type=Path), default=None)
@click.option("--run-root", type=click.Path(path_type=Path), default=None)
@click.option("--source-crs", default=None, help="Override source CRS when replaying a failed run.")
@click.option("--max-iterations", default=None, type=int, help="Override max iterations for the replayed run.")
@click.option("--mock/--live", "use_mock", default=None, help="Use mock or live LiteLLM routing.")
@click.option("--dry-run", is_flag=True, help="Print the reconstructed replay task without executing it.")
@click.option("--confirm", is_flag=True, help="Required to execute a replay against local data.")
def replay_last_command(
    run_id: str | None,
    state_file: Path | None,
    run_root: Path | None,
    source_crs: str | None,
    max_iterations: int | None,
    use_mock: bool | None,
    dry_run: bool,
    confirm: bool,
) -> None:
    """Replay the latest failed run using its stored task context."""
    from .agent_loop import AgentTask
    from .goal_runner import run_agent_task
    from .state_store import StateStore

    config = _load_runtime_config(
        state_file=state_file,
        run_root=run_root,
        use_mock=use_mock,
        max_iterations=max_iterations,
    )

    store = StateStore(config.state_file, config.run_root)
    task_payload = store.task_for_run(run_id) if run_id is not None else store.latest_failed_task()
    if task_payload is None:
        raise click.ClickException("No matching run snapshots are available.")

    task = AgentTask(
        task_summary=task_payload["task_summary"],
        vector_path=task_payload["vector_path"],
        raster_path=task_payload.get("raster_path"),
        source_crs=source_crs if source_crs is not None else task_payload.get("source_crs"),
        max_iterations=max_iterations if max_iterations is not None else task_payload.get("max_iterations", config.max_iterations),
        template_id=task_payload.get("template_id"),
        template_title=task_payload.get("template_title"),
    )
    if dry_run:
        _dump(
            {
                "mode": "dry-run",
                "run_id": run_id,
                "task": task.to_dict(),
                "rerun_command": _render_rerun_command(task.to_dict()),
            }
        )
        return
    if not confirm:
        raise click.ClickException("Replay execution requires --confirm. Use --dry-run to inspect the task first.")
    result = run_agent_task(task, config)
    _dump(result.to_dict())
    if result.status != "succeeded":
        raise click.exceptions.Exit(1)


@main.command("export-report")
@click.option("--run-id", default=None, help="Export a report bundle for a specific run id instead of the latest failed run.")
@click.option("--latest-failed", is_flag=True, help="Explicitly export the latest failed run.")
@click.option("--profile", default=None, help="Predefined report profile: quick, full, or debug.")
@click.option(
    "--only",
    default=None,
    help="Comma-separated subset of report sections to export: summary,state,failure-files,replay,adoption,index.",
)
@click.option("--print-index", is_flag=True, help="Print the generated report index instead of the default JSON summary.")
@click.option("--output-dir", type=click.Path(path_type=Path), default=None, help="Directory that will receive the report files.")
@click.option("--state-file", type=click.Path(path_type=Path), default=None)
@click.option("--run-root", type=click.Path(path_type=Path), default=None)
def export_report_command(
    run_id: str | None,
    latest_failed: bool,
    profile: str | None,
    only: str | None,
    print_index: bool,
    output_dir: Path | None,
    state_file: Path | None,
    run_root: Path | None,
) -> None:
    """Export a local recovery report bundle for the selected failed run."""
    from .state_store import StateStore

    if run_id is not None and latest_failed:
        raise click.ClickException("Use either --run-id or --latest-failed, not both.")
    if profile is not None and only is not None:
        raise click.ClickException("Use either --profile or --only, not both.")

    selected_sections = None
    if profile:
        profiles = {
            "quick": {"summary", "replay", "adoption", "index"},
            "full": {"summary", "state", "failure-files", "replay", "adoption", "index"},
            "debug": {"state", "failure-files", "replay", "index"},
        }
        if profile not in profiles:
            raise click.ClickException("Unsupported profile. Use quick, full, or debug.")
        selected_sections = profiles[profile]
    if only:
        selected_sections = {item.strip() for item in only.split(",") if item.strip()}
        allowed_sections = {"summary", "state", "failure-files", "replay", "adoption", "index"}
        unknown = selected_sections - allowed_sections
        if unknown:
            raise click.ClickException(f"Unsupported report section(s): {', '.join(sorted(unknown))}")
    if print_index and selected_sections is not None:
        selected_sections = set(selected_sections)
        selected_sections.add("index")

    config = _load_runtime_config(state_file=state_file, run_root=run_root)
    store = StateStore(config.state_file, config.run_root)

    if run_id is not None:
        summary = store.run_summary(run_id)
    else:
        summary = store.latest_failed_run_summary()
    files_payload = None
    replay_payload = None
    if summary is not None:
        selected_run_id = summary["run_id"]
        log_dir = Path(config.run_root) / "logs" / selected_run_id
        failed_dir = Path(config.run_root) / "failed"
        files_payload = {
            **summary,
            "log_dir": str(log_dir),
            "log_json_files": sorted(str(path) for path in log_dir.glob("*.json")) if log_dir.exists() else [],
            "log_py_files": sorted(str(path) for path in log_dir.glob("*.py")) if log_dir.exists() else [],
            "failed_scripts": sorted(str(path) for path in failed_dir.glob(f"{selected_run_id}-*.py")) if failed_dir.exists() else [],
        }
        task = store.task_for_run(selected_run_id)
        if task is not None:
            replay_payload = {
                **summary,
                "rerun_command": _render_rerun_command(task),
                "suggested_fix": summary.get("next_step_hint"),
            }

    if summary is None or files_payload is None or replay_payload is None:
        raise click.ClickException("No matching run snapshots are available.")

    run_rows = store.rows_for_run(summary["run_id"])
    adoption_payload = store.adoption_report(summary["run_id"])

    if output_dir is None:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        output_dir = Path("reports") / f"{summary['run_id']}-{timestamp}"

    entries: dict[str, str] = {}
    if selected_sections is None or "summary" in selected_sections:
        entries["summary.json"] = _render_json(summary)
        entries["summary.txt"] = _render_replay_table({**summary, "suggested_fix": summary.get("next_step_hint")})
    if selected_sections is None or "state" in selected_sections:
        entries["state.json"] = _render_json(run_rows)
        entries["state.txt"] = _render_state_table(run_rows)
    if selected_sections is None or "failure-files" in selected_sections:
        entries["failure-files.json"] = _render_json(files_payload)
        entries["failure-files.txt"] = _render_failure_files_table(files_payload)
    if selected_sections is None or "replay" in selected_sections:
        entries["replay.json"] = _render_json(replay_payload)
        entries["replay.txt"] = _render_replay_table(replay_payload)
    if selected_sections is None or "adoption" in selected_sections:
        if adoption_payload is None:
            raise click.ClickException("Unable to build the adoption report for this run.")
        entries["adoption.json"] = _render_json(adoption_payload)
        entries["adoption.txt"] = _render_adoption_report_text(adoption_payload)
    written = _write_report_bundle(output_dir, entries)
    index_text = None
    if selected_sections is None or "index" in selected_sections:
        final_written = {
            **written,
            "index.json": str(output_dir / "index.json"),
            "index.txt": str(output_dir / "index.txt"),
        }
        index_payload = {
            "run_id": summary["run_id"],
            "output_dir": str(output_dir),
            "summary": summary["summary"],
            "suggested_fix": summary.get("next_step_hint"),
            "files": final_written,
        }
        index_text = _render_index_text(index_payload)
        _write_report_bundle(
            output_dir,
            {
                "index.json": _render_json(index_payload),
                "index.txt": index_text,
            },
        )
        written = final_written

    payload = {
        "run_id": summary["run_id"],
        "output_dir": str(output_dir),
        "files": written,
    }
    if print_index:
        if index_text is None:
            raise click.ClickException("Unable to print the index for this report bundle.")
        _emit_text(index_text)
        return
    _dump(payload)


if __name__ == "__main__":
    main()
