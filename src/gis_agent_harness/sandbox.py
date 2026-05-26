from __future__ import annotations

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
    def __init__(self, run_root: str | Path, timeout_seconds: int = 20) -> None:
        self.run_root = Path(run_root)
        self.timeout_seconds = timeout_seconds
        ensure_run_dirs(self.run_root)
        self.working_directory = self.run_root.resolve().parent

    def _write_failed_copy(self, run_id: str, step_name: str, script_text: str) -> Path:
        failed_path = self.run_root / "failed" / f"{run_id}-{step_name}.py"
        failed_path.write_text(script_text, encoding="utf-8")
        return failed_path

    def run_python(self, script_text: str, *, run_id: str, step_name: str) -> SandboxResult:
        ensure_run_dirs(self.run_root)
        report: GuardrailReport = validate_python_script(script_text)
        log_dir = self.run_root / "logs" / run_id
        log_dir.mkdir(parents=True, exist_ok=True)
        script_path = log_dir / f"{step_name}.py"
        script_path.write_text(script_text, encoding="utf-8")
        resolved_script_path = script_path.resolve()

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
            )
            write_json(log_dir / f"{step_name}.json", result.to_dict())
            return result

        if not result.success:
            self._write_failed_copy(run_id, step_name, script_text)

        write_json(log_dir / f"{step_name}.json", result.to_dict())
        return result
