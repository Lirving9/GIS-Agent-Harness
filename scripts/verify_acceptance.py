from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

REQUIRED_PATHS = [
    "AGENTS.md",
    "AGENT_STATE.md",
    "README.md",
    "pyproject.toml",
    "requirements.txt",
    ".env.example",
    "litellm-config.yaml",
    ".codex/config.toml",
    "Dockerfile",
    ".dockerignore",
    ".github/workflows/ci.yml",
    "docs/architecture.md",
    "docs/operations.md",
    "scripts/generate_sample_data.py",
    "scripts/demo_task.py",
    "scripts/demo_recovery.py",
    "scripts/demo_readme_workflow.py",
    "scripts/demo_failures.py",
    "scripts/clean_local_state.py",
    "src/gis_agent_harness/__init__.py",
    "src/gis_agent_harness/cli.py",
    "src/gis_agent_harness/config.py",
    "src/gis_agent_harness/auth_config.py",
    "src/gis_agent_harness/goal_runner.py",
    "src/gis_agent_harness/execution_plan.py",
    "src/gis_agent_harness/task_templates.py",
    "src/gis_agent_harness/llm_adapters.py",
    "src/gis_agent_harness/llm_router.py",
    "src/gis_agent_harness/review.py",
    "src/gis_agent_harness/qgis_process.py",
    "src/gis_agent_harness/spatial_context.py",
    "src/gis_agent_harness/spatial_tools.py",
    "src/gis_agent_harness/guardrails.py",
    "src/gis_agent_harness/sandbox.py",
    "src/gis_agent_harness/agent_loop.py",
    "src/gis_agent_harness/state_store.py",
    "src/gis_agent_harness/state_hooks.py",
    "src/gis_agent_harness/telemetry.py",
    "src/gis_agent_harness/mcp_registry.py",
    "src/gis_agent_harness/parameter_alignment.py",
    "src/gis_agent_harness/visual_artifacts.py",
    "src/gis_agent_harness/visual_judge.py",
    "src/gis_agent_harness/stac_discovery.py",
    "src/gis_agent_harness/resource_router.py",
    "src/gis_agent_harness/faas_planner.py",
    "src/gis_agent_harness/qgis_plugin.py",
    "src/gis_agent_harness/cog_viewer.py",
    "src/gis_agent_harness/benchmarking.py",
    "src/gis_agent_harness/adversarial_review.py",
    "src/gis_agent_harness/geo_exception_parser.py",
    "src/gis_agent_harness/pipeline_reporting.py",
    "src/gis_agent_harness/mcp_runtime.py",
    "src/gis_agent_harness/dag_runner.py",
    "src/gis_agent_harness/context_compaction.py",
    "src/gis_agent_harness/narrative_report.py",
    "src/gis_agent_harness/requirement_matrix.py",
    "src/gis_agent_harness/tui/__init__.py",
    "src/gis_agent_harness/tui/app.py",
    "src/gis_agent_harness/tui/screens.py",
    "src/gis_agent_harness/tui/widgets.py",
    "src/gis_agent_harness/logging_utils.py",
    "src/gis_agent_harness/prompts.py",
    "src/gis_agent_harness/errors.py",
    "goals/align_vector_to_raster.yaml",
    "goals/declare_source_crs.yaml",
    "goals/repair_invalid_geometry.yaml",
    "plans/declare_source_crs.yaml",
    "tests/conftest.py",
    "tests/test_cli.py",
    "tests/test_spatial_tools.py",
    "tests/test_guardrails.py",
    "tests/test_agent_loop.py",
    "tests/test_e2e_smoke.py",
    "tests/test_templates.py",
    "tests/test_goal_cli.py",
    "tests/test_execution_plan.py",
    "tests/test_llm_adapters.py",
    "tests/test_review.py",
    "tests/test_spatial_context.py",
    "tests/test_telemetry.py",
    "tests/test_tui_smoke.py",
    "tests/test_advanced_geoai.py",
    "tests/test_blueprint_execution.py",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify GIS Agent Harness acceptance criteria locally.")
    parser.add_argument(
        "--skip-pytest",
        action="store_true",
        help="Skip the full pytest run. Useful when smoke-testing this verifier from inside pytest.",
    )
    return parser.parse_args()


def run_command(
    args: list[str],
    *,
    env: dict[str, str],
    cwd: Path,
    expect_success: bool = True,
) -> tuple[int, str, str]:
    result = subprocess.run(
        args,
        capture_output=True,
        text=True,
        check=False,
        env=env,
        cwd=cwd,
    )
    if expect_success and result.returncode != 0:
        raise SystemExit(result.stderr or result.stdout or f"Command failed: {' '.join(args)}")
    if not expect_success and result.returncode == 0:
        raise SystemExit(f"Command unexpectedly succeeded: {' '.join(args)}")
    return result.returncode, result.stdout, result.stderr


def run_script(path: str, *, env: dict[str, str]) -> dict[str, Any]:
    _, stdout, _ = run_command([sys.executable, str(ROOT / path)], env=env, cwd=ROOT)
    return json.loads(stdout)


def main() -> None:
    args = parse_args()
    env_base = os.environ.copy()
    env_base["PYTHONPATH"] = str(SRC)

    deliverables = {path: (ROOT / path).exists() for path in REQUIRED_PATHS}

    with tempfile.TemporaryDirectory(prefix="gis-harness-acceptance-") as temp_dir:
        temp_root = Path(temp_dir)

        task_env = {
            **env_base,
            "GIS_AGENT_HARNESS_RUN_ROOT": str(temp_root / "demo-task" / ".runs"),
            "GIS_AGENT_HARNESS_STATE_FILE": str(temp_root / "demo-task" / "AGENT_STATE.md"),
            "GIS_AGENT_HARNESS_FIXTURE_DIR": str(temp_root / "demo-task" / "fixtures"),
        }
        recovery_env = {
            **env_base,
            "GIS_AGENT_HARNESS_RUN_ROOT": str(temp_root / "demo-recovery" / ".runs"),
            "GIS_AGENT_HARNESS_STATE_FILE": str(temp_root / "demo-recovery" / "AGENT_STATE.md"),
            "GIS_AGENT_HARNESS_FIXTURE_DIR": str(temp_root / "demo-recovery" / "fixtures"),
        }
        readme_env = {
            **env_base,
            "GIS_AGENT_HARNESS_RUN_ROOT": str(temp_root / "demo-readme" / ".runs"),
            "GIS_AGENT_HARNESS_STATE_FILE": str(temp_root / "demo-readme" / "AGENT_STATE.md"),
            "GIS_AGENT_HARNESS_FIXTURE_DIR": str(temp_root / "demo-readme" / "fixtures"),
        }
        failures_env = {
            **env_base,
            "GIS_AGENT_HARNESS_RUN_ROOT": str(temp_root / "demo-failures" / ".runs"),
        }

        task_payload = run_script("scripts/demo_task.py", env=task_env)
        recovery_payload = run_script("scripts/demo_recovery.py", env=recovery_env)
        readme_payload = run_script("scripts/demo_readme_workflow.py", env=readme_env)
        failures_payload = run_script("scripts/demo_failures.py", env=failures_env)

        recovery_state_file = Path(recovery_env["GIS_AGENT_HARNESS_STATE_FILE"])
        recovery_state_text = recovery_state_file.read_text(encoding="utf-8")
        readme_run_root = Path(readme_env["GIS_AGENT_HARNESS_RUN_ROOT"])
        readme_state_file = Path(readme_env["GIS_AGENT_HARNESS_STATE_FILE"])

        _, spatial_map_stdout, _ = run_command(
            [
                sys.executable,
                "-m",
                "gis_agent_harness.cli",
                "spatial-map",
                str(Path(readme_env["GIS_AGENT_HARNESS_FIXTURE_DIR"])),
            ],
            env=readme_env,
            cwd=ROOT,
        )
        spatial_map_payload = json.loads(spatial_map_stdout)

        _, qgis_stdout, _ = run_command(
            [
                sys.executable,
                "-m",
                "gis_agent_harness.cli",
                "qgis-run",
                "native:buffer",
                "--payload-json",
                '{"inputs": {"INPUT": "roads.gpkg", "DISTANCE": 500}}',
            ],
            env=readme_env,
            cwd=ROOT,
        )
        qgis_payload = json.loads(qgis_stdout)

        first_readme_run = readme_payload["succeeded_run"]["run_id"]
        _, adoption_stdout, _ = run_command(
            [
                sys.executable,
                "-m",
                "gis_agent_harness.cli",
                "adoption-report",
                first_readme_run,
                "--state-file",
                str(readme_state_file),
                "--run-root",
                str(readme_run_root),
            ],
            env=readme_env,
            cwd=ROOT,
        )
        adoption_payload = json.loads(adoption_stdout)

        advanced_dir = temp_root / "advanced"
        advanced_dir.mkdir(parents=True, exist_ok=True)
        visual_path = advanced_dir / "map.png"
        visual_path.write_bytes(
            bytes.fromhex(
                "89504e470d0a1a0a0000000d4948445200000001000000010804000000b50c0c020000000b4944415478da63fcff1f0003030200efbfa7db0000000049454e44ae426082"
            )
        )
        route_script = advanced_dir / "gpu-script.py"
        route_script.write_text("import torch\n", encoding="utf-8")
        junit_path = advanced_dir / "benchmark.xml"
        cog_viewer_path = advanced_dir / "viewer.html"

        _, mcp_stdout, _ = run_command(
            [
                sys.executable,
                "-m",
                "gis_agent_harness.cli",
                "mcp-tools",
                "--domain",
                "raster",
            ],
            env=readme_env,
            cwd=ROOT,
        )
        mcp_payload = json.loads(mcp_stdout)

        _, align_stdout, _ = run_command(
            [
                sys.executable,
                "-m",
                "gis_agent_harness.cli",
                "align-params",
                "--params-json",
                '{"target_crs": 4326, "bbox": "-1,-2,3,4", "distance": "500"}',
            ],
            env=readme_env,
            cwd=ROOT,
        )
        align_payload = json.loads(align_stdout)

        _, capture_stdout, _ = run_command(
            [
                sys.executable,
                "-m",
                "gis_agent_harness.cli",
                "capture-artifact",
                str(visual_path),
                "--output-dir",
                str(advanced_dir / "captures"),
            ],
            env=readme_env,
            cwd=ROOT,
        )
        capture_payload = json.loads(capture_stdout)

        _, judge_stdout, _ = run_command(
            [
                sys.executable,
                "-m",
                "gis_agent_harness.cli",
                "judge-map",
                str(visual_path),
                "--criteria-json",
                '{"required_layers": ["buildings"], "observed_layers": [], "legend_required": true, "legend_present": false}',
                "--output-dir",
                str(advanced_dir / "captures"),
            ],
            env=readme_env,
            cwd=ROOT,
        )
        judge_payload = json.loads(judge_stdout)

        _, stac_stdout, _ = run_command(
            [
                sys.executable,
                "-m",
                "gis_agent_harness.cli",
                "stac-plan",
                "--collection",
                "sentinel-2-l2a",
                "--bbox",
                "-60,-4,-59,-3",
                "--datetime",
                "2023-06-01/2023-08-31",
                "--max-cloud-cover",
                "20",
            ],
            env=readme_env,
            cwd=ROOT,
        )
        stac_payload = json.loads(stac_stdout)

        _, route_stdout, _ = run_command(
            [
                sys.executable,
                "-m",
                "gis_agent_harness.cli",
                "route-resource",
                "--script-file",
                str(route_script),
            ],
            env=readme_env,
            cwd=ROOT,
        )
        route_payload = json.loads(route_stdout)

        _, faas_stdout, _ = run_command(
            [
                sys.executable,
                "-m",
                "gis_agent_harness.cli",
                "faas-manifest",
                "--function-name",
                "segment-cog",
                "--image",
                "gis-agent-harness:local",
                "--handler",
                "functions.segment:handler",
                "--input-asset",
                "file:///tmp/input.tif",
                "--script-file",
                str(route_script),
            ],
            env=readme_env,
            cwd=ROOT,
        )
        faas_payload = json.loads(faas_stdout)

        _, qgis_plugin_stdout, _ = run_command(
            [
                sys.executable,
                "-m",
                "gis_agent_harness.cli",
                "qgis-plugin-manifest",
                "--plugin-name",
                "GISAgentMCPBridge",
            ],
            env=readme_env,
            cwd=ROOT,
        )
        qgis_plugin_payload = json.loads(qgis_plugin_stdout)

        _, cog_stdout, _ = run_command(
            [
                sys.executable,
                "-m",
                "gis_agent_harness.cli",
                "cog-viewer",
                "--output-html",
                str(cog_viewer_path),
                "--cog-url",
                "file:///tmp/result.tif",
                "--title",
                "COG Acceptance",
            ],
            env=readme_env,
            cwd=ROOT,
        )
        cog_payload = json.loads(cog_stdout)

        _, benchmark_stdout, _ = run_command(
            [
                sys.executable,
                "-m",
                "gis_agent_harness.cli",
                "benchmark-manifest",
                "--junit-file",
                str(junit_path),
            ],
            env=readme_env,
            cwd=ROOT,
        )
        benchmark_payload = json.loads(benchmark_stdout)

        _, method_stdout, _ = run_command(
            [
                sys.executable,
                "-m",
                "gis_agent_harness.cli",
                "method-review",
                "--analysis-json",
                '{"method": "ordinary least squares on polygons", "crs": "EPSG:4326", "notes": "No spatial autocorrelation check was recorded."}',
                "--max-rounds",
                "2",
            ],
            env=readme_env,
            cwd=ROOT,
        )
        method_payload = json.loads(method_stdout)

        _, exception_stdout, _ = run_command(
            [
                sys.executable,
                "-m",
                "gis_agent_harness.cli",
                "explain-exception",
                "GEOSException: TopologyException: Self-intersection",
            ],
            env=readme_env,
            cwd=ROOT,
        )
        exception_payload = json.loads(exception_stdout)

        _, mcp_call_stdout, _ = run_command(
            [
                sys.executable,
                "-m",
                "gis_agent_harness.cli",
                "mcp-call",
                "inspect-vector",
                "--params-json",
                json.dumps({"path": readme_payload["inspect_vector"]["path"], "sample_size": 1}),
            ],
            env=readme_env,
            cwd=ROOT,
        )
        mcp_call_payload = json.loads(mcp_call_stdout)

        _, compact_stdout, _ = run_command(
            [
                sys.executable,
                "-m",
                "gis_agent_harness.cli",
                "compact-failures",
                "--history-json",
                json.dumps(
                    [
                        {"action": "gdalwarp", "parameters": {"s_srs": "bad"}, "status": "failed"},
                        {"action": "gdalwarp", "parameters": {"s_srs": "bad"}, "status": "failed"},
                        {"action": "gdalwarp", "parameters": {"s_srs": "bad"}, "status": "failed"},
                    ]
                ),
            ],
            env=readme_env,
            cwd=ROOT,
        )
        compact_payload = json.loads(compact_stdout)

        _, benchmark_run_stdout, _ = run_command(
            [
                sys.executable,
                "-m",
                "gis_agent_harness.cli",
                "benchmark-run",
            ],
            env=readme_env,
            cwd=ROOT,
        )
        benchmark_run_payload = json.loads(benchmark_run_stdout)

        _, requirement_matrix_stdout, _ = run_command(
            [
                sys.executable,
                "-m",
                "gis_agent_harness.cli",
                "requirement-matrix",
            ],
            env=readme_env,
            cwd=ROOT,
        )
        requirement_matrix_payload = json.loads(requirement_matrix_stdout)

        adoption_json_file = advanced_dir / "adoption.json"
        adoption_json_file.write_text(json.dumps(adoption_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        narrative_path = advanced_dir / "NARRATIVE_REPORT.md"
        _, narrative_stdout, _ = run_command(
            [
                sys.executable,
                "-m",
                "gis_agent_harness.cli",
                "narrative-report",
                "--adoption-json-file",
                str(adoption_json_file),
                "--output-file",
                str(narrative_path),
            ],
            env=readme_env,
            cwd=ROOT,
        )
        narrative_payload = json.loads(narrative_stdout)

        cli_help_ok = readme_payload["help_has_core_commands"] is True
        vector_probe_ok = all(
            key in readme_payload["inspect_vector"] for key in ["driver", "crs", "bounds", "schema", "sample_records"]
        )
        raster_probe_ok = all(
            key in readme_payload["inspect_raster"]
            for key in ["width", "height", "count", "dtypes", "nodatavals", "crs", "bounds", "transform"]
        )
        crs_guardrails_ok = (
            recovery_payload["initial_failure"]["observations"][0]["code"] == "missing_crs"
            and readme_payload["succeeded_run"]["decisions"][0]["action"] == "to_crs"
        )
        sandbox_ok = failures_payload["blocked"]["blocked_by_guardrails"] and failures_payload["timed_out"]["timed_out"]
        self_heal_ok = task_payload["status"] == "succeeded" and recovery_payload["recovery_run"]["status"] == "succeeded"
        goal_templates_ok = {
            item["template_id"] for item in readme_payload["templates_list"]
        } >= {"align_vector_to_raster", "declare_source_crs", "repair_invalid_geometry"}
        goal_run_ok = (
            readme_payload["goal_dry_run"]["task"]["template_id"] == "declare_source_crs"
            and readme_payload["goal_run"]["status"] == "succeeded"
        )
        plan_run_ok = readme_payload["goal_plan_run"]["status"] == "succeeded"
        config_doctor_ok = readme_payload["config_doctor"]["status"] == "ok"
        packaging_ok = all((ROOT / path).exists() for path in ["Dockerfile", ".dockerignore", ".github/workflows/ci.yml"])
        state_persistence_ok = all(
            text in recovery_state_text
            for text in ["# Agent State", "Summary:", "Suggested fix:", "stop | failed", "complete | succeeded"]
        )
        spatial_context_ok = (
            spatial_map_payload["dataset_count"] >= 2
            and any(item["kind"] == "vector" and item.get("crs") for item in spatial_map_payload["datasets"])
            and any(item["kind"] == "raster" and item.get("raster", {}).get("band_count") for item in spatial_map_payload["datasets"])
        )
        progressive_context_ok = (
            readme_payload["spatial_map_detail"]["kind"] == "vector"
            and readme_payload["spatial_map_detail"]["feature_count"] is not None
        )
        qgis_json_ok = (
            qgis_payload["success"] is True
            and qgis_payload["dry_run"] is True
            and qgis_payload["algorithm"] == "native:buffer"
            and qgis_payload["parameters"]["inputs"]["DISTANCE"] == 500
            and qgis_payload["risk"]["payload_bytes"] > 0
        )
        telemetry_ok = (
            readme_payload["telemetry_summary"]["event_counts"].get("decision_review", 0) >= 1
            and readme_payload["telemetry_summary"]["event_counts"].get("sandbox_execution", 0) >= 1
        )
        adoption_report_ok = (
            adoption_payload["run_id"] == first_readme_run
            and bool(adoption_payload["source_data"])
            and bool(adoption_payload["actions"])
            and bool(adoption_payload["lineage"]["nodes"])
        )
        documentation_ok = all(
            (ROOT / path).exists()
            for path in ["README.md", "docs/architecture.md", "docs/operations.md", "AGENTS.md", ".codex/config.toml"]
        )
        readme_commands_ok = readme_payload["replay_confirm"]["status"] == "succeeded"
        mcp_progressive_ok = (
            mcp_payload["protocol"] == "mcp-json-rpc"
            and mcp_payload["progressive_disclosure"] is True
            and {item["domain"] for item in mcp_payload["tools"]} == {"raster"}
        )
        parameter_alignment_ok = (
            align_payload["parameters"]["target_crs"] == "EPSG:4326"
            and align_payload["parameters"]["bbox"] == [-1.0, -2.0, 3.0, 4.0]
            and align_payload["parameters"]["distance"] == 500.0
        )
        visual_capture_ok = (
            capture_payload["content_type"] == "image/png"
            and bool(capture_payload["sha256"])
            and bool(capture_payload["thumbnail_base64"])
        )
        visual_judge_ok = (
            judge_payload["status"] == "needs_revision"
            and {item["code"] for item in judge_payload["issues"]} >= {"missing_layer", "missing_legend"}
        )
        stac_discovery_ok = (
            stac_payload["network_required"] is False
            and stac_payload["query"]["query"]["eo:cloud_cover"]["lt"] == 20
        )
        resource_routing_ok = route_payload["track"] == "gpu" and route_payload["container_profile"] == "geoai-gpu"
        faas_manifest_ok = (
            faas_payload["mode"] == "manifest-only"
            and faas_payload["resource_route"]["track"] == "gpu"
            and faas_payload["network_required"] is False
        )
        qgis_plugin_ok = (
            qgis_plugin_payload["transport"] == "mcp-json-rpc"
            and qgis_plugin_payload["approval_required"] is True
        )
        cog_viewer_ok = (
            cog_payload["exists"] is True
            and cog_viewer_path.exists()
            and "COG Acceptance" in cog_viewer_path.read_text(encoding="utf-8")
        )
        benchmark_pipeline_ok = (
            {"GeoAgentBench", "GeoBenchX", "GIS-Bench"} <= set(benchmark_payload["suites"])
            and junit_path.exists()
            and "testsuite" in junit_path.read_text(encoding="utf-8")
        )
        adversarial_review_ok = (
            method_payload["status"] == "needs_revision"
            and "spatial_autocorrelation" in {item["code"] for item in method_payload["findings"]}
        )
        exception_parser_ok = exception_payload["code"] == "invalid_geometry" and "make_valid" in exception_payload["suggested_fix"]
        mcp_runtime_ok = mcp_call_payload["success"] is True and mcp_call_payload["payload"]["driver"] == "GPKG"
        failure_compaction_ok = compact_payload["blocked"] is True and compact_payload["compacted_attempt_count"] == 3
        runnable_benchmarks_ok = benchmark_run_payload["status"] == "succeeded"
        requirement_matrix_ok = (
            requirement_matrix_payload["summary"]["implemented"] == requirement_matrix_payload["summary"]["total"]
        )
        narrative_report_ok = (
            narrative_payload["output_path"] == str(narrative_path)
            and narrative_path.exists()
            and "## Source Data" in narrative_path.read_text(encoding="utf-8")
        )

        pytest_result = {"ok": None, "stdout": "", "stderr": ""}
        if not args.skip_pytest:
            returncode, stdout, stderr = run_command([sys.executable, "-m", "pytest", "-q"], env=env_base, cwd=ROOT)
            pytest_result = {"ok": returncode == 0, "stdout": stdout, "stderr": stderr}

        acceptance = {
            "cli_usable": cli_help_ok,
            "vector_probe": vector_probe_ok,
            "raster_probe": raster_probe_ok,
            "goal_templates": goal_templates_ok,
            "goal_run": goal_run_ok,
            "goal_plan_run": plan_run_ok,
            "config_doctor": config_doctor_ok,
            "crs_guardrails": crs_guardrails_ok,
            "safe_execution": sandbox_ok,
            "self_heal_loop": self_heal_ok,
            "spatial_context_map": spatial_context_ok,
            "progressive_context_map": progressive_context_ok,
            "qgis_json_dry_run": qgis_json_ok,
            "telemetry_events": telemetry_ok,
            "adoption_report": adoption_report_ok,
            "state_persistence": state_persistence_ok,
            "packaging_ready": packaging_ok,
            "automated_tests": True if args.skip_pytest else bool(pytest_result["ok"]),
            "documentation_complete": documentation_ok,
            "mcp_progressive_tools": mcp_progressive_ok,
            "parameter_alignment": parameter_alignment_ok,
            "visual_artifact_capture": visual_capture_ok,
            "visual_judge": visual_judge_ok,
            "stac_discovery_plan": stac_discovery_ok,
            "resource_routing": resource_routing_ok,
            "faas_manifest": faas_manifest_ok,
            "qgis_plugin_manifest": qgis_plugin_ok,
            "cog_viewer_manifest": cog_viewer_ok,
            "benchmark_pipeline_manifest": benchmark_pipeline_ok,
            "adversarial_method_review": adversarial_review_ok,
            "geospatial_exception_parser": exception_parser_ok,
            "mcp_runtime_dispatch": mcp_runtime_ok,
            "failure_context_compaction": failure_compaction_ok,
            "runnable_benchmark_checks": runnable_benchmarks_ok,
            "requirement_matrix": requirement_matrix_ok,
            "narrative_report": narrative_report_ok,
        }
        stop_conditions = {
            "all_acceptance_items": all(acceptance.values()),
            "pytest_q": None if args.skip_pytest else bool(pytest_result["ok"]),
            "demo_task": task_payload["status"] == "succeeded",
            "readme_commands_copyable": readme_commands_ok,
            "goal_commands_copyable": goal_run_ok,
            "deliverables_present": all(deliverables.values()),
        }

        payload = {
            "deliverables": deliverables,
            "acceptance": acceptance,
            "stop_conditions": stop_conditions,
            "evidence": {
                "demo_task": task_payload,
                "demo_recovery": recovery_payload,
                "demo_readme_workflow": readme_payload,
                "demo_failures": failures_payload,
                "spatial_map": spatial_map_payload,
                "qgis_json": qgis_payload,
                "adoption_report": adoption_payload,
                "advanced_geoai": {
                    "mcp_tools": mcp_payload,
                    "aligned_parameters": align_payload,
                    "visual_capture": capture_payload,
                    "visual_judge": judge_payload,
                    "stac_plan": stac_payload,
                    "resource_route": route_payload,
                    "faas_manifest": faas_payload,
                    "qgis_plugin": qgis_plugin_payload,
                    "cog_viewer": cog_payload,
                    "benchmark_manifest": benchmark_payload,
                    "benchmark_run": benchmark_run_payload,
                    "method_review": method_payload,
                    "exception_parser": exception_payload,
                    "mcp_call": mcp_call_payload,
                    "context_compaction": compact_payload,
                    "requirement_matrix": requirement_matrix_payload,
                    "narrative_report": narrative_payload,
                },
                "recovery_state_file": str(recovery_state_file),
                "recovery_state_excerpt": recovery_state_text.splitlines()[:16],
                "pytest": pytest_result,
            },
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
