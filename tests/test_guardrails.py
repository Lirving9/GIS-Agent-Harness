from __future__ import annotations

from pathlib import Path

from gis_agent_harness.guardrails import preflight_dataset_checks, validate_python_script
from gis_agent_harness.sandbox import SandboxRunner


def test_ast_blocks_dangerous_imports() -> None:
    report = validate_python_script("import os\nos.system('echo nope')\n")
    assert not report.allowed
    assert any(item.code == "import_not_allowed" for item in report.observations)


def test_sandbox_risk_preview_collects_blocked_calls(tmp_path: Path) -> None:
    runner = SandboxRunner(tmp_path / ".runs")
    preview = runner.preview_script_risk("import os\nos.system('echo nope')\n")
    assert preview.allowed is False
    assert "os" in preview.blocked_imports
    assert "os.system" in preview.blocked_calls
    assert "dangerous_call" in preview.observation_codes


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
    assert "to_crs" not in (missing[0].suggested_fix or "")


def test_sandbox_timeout(tmp_path: Path) -> None:
    runner = SandboxRunner(tmp_path / ".runs", timeout_seconds=1)
    result = runner.run_python("while True:\n    pass\n", run_id="timeout", step_name="loop")
    assert result.timed_out
    assert not result.success


def test_sandbox_blocks_undeclared_pathlib_write_outside_write_root(tmp_path: Path) -> None:
    outside_path = tmp_path / "outside.txt"
    runner = SandboxRunner(tmp_path / ".runs", write_root=tmp_path / ".runs" / "artifacts")

    result = runner.run_python(
        f"from pathlib import Path\nPath(r'{outside_path}').write_text('escaped', encoding='utf-8')\n",
        run_id="escape",
        step_name="path-write",
        expected_output_path=tmp_path / ".runs" / "artifacts" / "declared.txt",
    )

    assert not result.success
    assert not outside_path.exists()
    assert "sandbox_write_outside_root" in {item.code for item in result.observations}


def test_sandbox_failed_if_write_violation_is_caught_by_script(tmp_path: Path) -> None:
    outside_path = tmp_path / "outside.txt"
    allowed_path = tmp_path / ".runs" / "artifacts" / "declared.txt"
    runner = SandboxRunner(tmp_path / ".runs", write_root=tmp_path / ".runs" / "artifacts")

    result = runner.run_python(
        "\n".join(
            [
                "from pathlib import Path",
                "try:",
                f"    Path(r'{outside_path}').write_text('escaped', encoding='utf-8')",
                "except PermissionError:",
                "    pass",
                f"Path(r'{allowed_path}').write_text('allowed', encoding='utf-8')",
            ]
        ),
        run_id="escape",
        step_name="caught-write",
        expected_output_path=allowed_path,
    )

    assert not result.success
    assert result.blocked_by_guardrails
    assert not outside_path.exists()
    assert allowed_path.exists()
    assert "sandbox_write_outside_root" in {item.code for item in result.observations}
