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
                "recovery_state_file": str(recovery_state_file),
                "recovery_state_excerpt": recovery_state_text.splitlines()[:16],
                "pytest": pytest_result,
            },
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
