from __future__ import annotations

import ast
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .errors import Observation
from .guardrails import GuardrailReport, validate_python_script
from .logging_utils import ensure_run_dirs, write_json


@dataclass(slots=True)
class SandboxRiskPreview:
    allowed: bool
    imports: list[str] = field(default_factory=list)
    blocked_imports: list[str] = field(default_factory=list)
    blocked_calls: list[str] = field(default_factory=list)
    observation_codes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SandboxResult:
    script_path: str
    command: list[str]
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool
    duration_seconds: float
    blocked_by_guardrails: bool = False
    observations: list[Observation] = field(default_factory=list)
    expected_output_path: str | None = None
    allowed_write_root: str | None = None
    risk_preview: dict[str, Any] | None = None

    @property
    def success(self) -> bool:
        return not self.blocked_by_guardrails and not self.timed_out and self.returncode == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "script_path": self.script_path,
            "command": self.command,
            "returncode": self.returncode,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "timed_out": self.timed_out,
            "duration_seconds": self.duration_seconds,
            "blocked_by_guardrails": self.blocked_by_guardrails,
            "observations": [asdict(item) for item in self.observations],
            "expected_output_path": self.expected_output_path,
            "allowed_write_root": self.allowed_write_root,
            "risk_preview": self.risk_preview,
            "success": self.success,
        }

    def to_observation(self) -> Observation:
        if self.observations:
            return self.observations[0]
        if self.timed_out:
            return Observation(
                code="sandbox_timeout",
                message=f"Sandbox execution timed out after {self.duration_seconds:.2f} seconds.",
                suggested_fix="Reduce the generated work or tighten the repair script.",
            )
        return Observation(
            code="sandbox_execution_failed",
            message="Sandbox execution failed.",
            suggested_fix="Inspect stderr and the archived script under .runs/failed/.",
            details={"stderr": self.stderr, "stdout": self.stdout},
        )


class SandboxRunner:
    def __init__(
        self,
        run_root: str | Path,
        timeout_seconds: int = 20,
        *,
        write_root: str | Path | None = None,
    ) -> None:
        self.run_root = Path(run_root)
        self.timeout_seconds = timeout_seconds
        ensure_run_dirs(self.run_root)
        self.working_directory = self.run_root.resolve().parent
        self.write_root = Path(write_root) if write_root is not None else self.run_root / "artifacts"

    def _write_failed_copy(self, run_id: str, step_name: str, script_text: str) -> Path:
        failed_path = self.run_root / "failed" / f"{run_id}-{step_name}.py"
        failed_path.write_text(script_text, encoding="utf-8")
        return failed_path

    def preview_script_risk(self, script_text: str) -> SandboxRiskPreview:
        report: GuardrailReport = validate_python_script(script_text)
        imports: list[str] = []
        try:
            tree = ast.parse(script_text)
        except SyntaxError:
            return SandboxRiskPreview(
                allowed=False,
                observation_codes=[item.code for item in report.observations],
            )
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)
        blocked_imports = [
            item.details.get("name", item.message)
            for item in report.observations
            if item.code == "import_not_allowed"
        ]
        blocked_calls = [
            item.details.get("name", item.message)
            for item in report.observations
            if item.code == "call_not_allowed"
        ]
        return SandboxRiskPreview(
            allowed=report.allowed,
            imports=sorted(set(imports)),
            blocked_imports=sorted(set(str(item) for item in blocked_imports)),
            blocked_calls=sorted(set(str(item) for item in blocked_calls)),
            observation_codes=[item.code for item in report.observations],
        )

    def _output_path_allowed(self, expected_output_path: str | Path | None) -> bool:
        if expected_output_path is None:
            return True
        try:
            Path(expected_output_path).resolve().relative_to(self.write_root.resolve())
            return True
        except ValueError:
            return False

    def run_python(
        self,
        script_text: str,
        *,
        run_id: str,
        step_name: str,
        expected_output_path: str | Path | None = None,
    ) -> SandboxResult:
        ensure_run_dirs(self.run_root)
        report: GuardrailReport = validate_python_script(script_text)
        risk_preview = self.preview_script_risk(script_text)
        log_dir = self.run_root / "logs" / run_id
        log_dir.mkdir(parents=True, exist_ok=True)
        script_path = log_dir / f"{step_name}.py"
        script_path.write_text(script_text, encoding="utf-8")
        resolved_script_path = script_path.resolve()

        if not self._output_path_allowed(expected_output_path):
            observation = Observation(
                code="sandbox_output_path_blocked",
                message=(
                    f"Output path {Path(expected_output_path).resolve()} is outside the allowed "
                    f"write root {self.write_root.resolve()}."
                ),
                suggested_fix="Write sandbox artifacts under the configured artifact directory.",
                details={
                    "expected_output_path": str(Path(expected_output_path).resolve()),
                    "allowed_write_root": str(self.write_root.resolve()),
                },
            )
            self._write_failed_copy(run_id, step_name, script_text)
            result = SandboxResult(
                script_path=str(resolved_script_path),
                command=[sys.executable, str(resolved_script_path)],
                returncode=1,
                stdout="",
                stderr="Blocked by sandbox output policy.",
                timed_out=False,
                duration_seconds=0.0,
                blocked_by_guardrails=True,
                observations=[observation],
                expected_output_path=str(Path(expected_output_path).resolve()),
                allowed_write_root=str(self.write_root.resolve()),
                risk_preview=risk_preview.to_dict(),
            )
            write_json(log_dir / f"{step_name}.json", result.to_dict())
            return result

        if not report.allowed:
            self._write_failed_copy(run_id, step_name, script_text)
            result = SandboxResult(
                script_path=str(resolved_script_path),
                command=[sys.executable, str(resolved_script_path)],
                returncode=1,
                stdout="",
                stderr="Blocked by guardrails.",
                timed_out=False,
                duration_seconds=0.0,
                blocked_by_guardrails=True,
                observations=report.observations,
                expected_output_path=str(expected_output_path) if expected_output_path else None,
                allowed_write_root=str(self.write_root.resolve()),
                risk_preview=risk_preview.to_dict(),
            )
            write_json(log_dir / f"{step_name}.json", result.to_dict())
            return result

        command = [sys.executable, str(resolved_script_path)]
        started = time.perf_counter()
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                cwd=self.working_directory,
                check=False,
            )
            duration = time.perf_counter() - started
            result = SandboxResult(
                script_path=str(resolved_script_path),
                command=command,
                returncode=completed.returncode,
                stdout=completed.stdout,
                stderr=completed.stderr,
                timed_out=False,
                duration_seconds=duration,
                expected_output_path=str(expected_output_path) if expected_output_path else None,
                allowed_write_root=str(self.write_root.resolve()),
                risk_preview=risk_preview.to_dict(),
            )
        except subprocess.TimeoutExpired as exc:
            duration = time.perf_counter() - started
            self._write_failed_copy(run_id, step_name, script_text)
            result = SandboxResult(
                script_path=str(resolved_script_path),
                command=command,
                returncode=124,
                stdout=exc.stdout or "",
                stderr=exc.stderr or "",
                timed_out=True,
                duration_seconds=duration,
                expected_output_path=str(expected_output_path) if expected_output_path else None,
                allowed_write_root=str(self.write_root.resolve()),
                risk_preview=risk_preview.to_dict(),
            )
            write_json(log_dir / f"{step_name}.json", result.to_dict())
            return result

        if not result.success:
            self._write_failed_copy(run_id, step_name, script_text)

        write_json(log_dir / f"{step_name}.json", result.to_dict())
        return result
