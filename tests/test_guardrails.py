from __future__ import annotations

from pathlib import Path

from gis_agent_harness.guardrails import preflight_dataset_checks, validate_python_script
from gis_agent_harness.sandbox import SandboxRunner


def test_ast_blocks_dangerous_imports() -> None:
    report = validate_python_script("import os\nos.system('echo nope')\n")
    assert not report.allowed
    assert any(item.code == "import_not_allowed" for item in report.observations)


def test_preflight_detects_crs_mismatch(fixture_paths: dict[str, str]) -> None:
    observations = preflight_dataset_checks(
        fixture_paths["sample_3857"],
        fixture_paths["sample_raster"],
    )
    assert any(item.code == "crs_mismatch" for item in observations)


def test_preflight_detects_missing_crs(fixture_paths: dict[str, str]) -> None:
    observations = preflight_dataset_checks(fixture_paths["missing_crs"])
    missing = [item for item in observations if item.code == "missing_crs"]
    assert missing
    assert "set_crs" in (missing[0].suggested_fix or "")


def test_sandbox_timeout(tmp_path: Path) -> None:
    runner = SandboxRunner(tmp_path / ".runs", timeout_seconds=1)
    result = runner.run_python("while True:\n    pass\n", run_id="timeout", step_name="loop")
    assert result.timed_out
    assert not result.success
