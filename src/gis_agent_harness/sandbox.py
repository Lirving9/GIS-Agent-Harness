from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .errors import Observation
from .guardrails import GuardrailReport, validate_python_script
from .logging_utils import ensure_run_dirs, write_json

SANDBOX_WRITE_VIOLATION_CODE = 73
SANDBOX_WRITE_VIOLATION_MARKER = "GIS_SANDBOX_WRITE_OUTSIDE_ROOT "


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

    def _build_runtime_wrapper(self, script_path: Path) -> str:
        return f"""from __future__ import annotations

import builtins
import io
import json
import pathlib
import runpy
import sys

_ALLOWED_WRITE_ROOT = pathlib.Path({str(self.write_root.resolve())!r}).resolve()
_SCRIPT_PATH = pathlib.Path({str(script_path.resolve())!r}).resolve()
_ORIGINAL_OPEN = builtins.open
_ORIGINAL_IO_OPEN = io.open
_ORIGINAL_IMPORT = builtins.__import__
_PATCHED_MODULES = set()


class _SandboxWriteViolation(PermissionError):
    pass


def _is_write_mode(mode):
    return any(flag in str(mode) for flag in ("w", "a", "x", "+"))


def _resolve_path(path):
    return pathlib.Path(path).expanduser().resolve()


def _assert_write_allowed(path):
    resolved = _resolve_path(path)
    try:
        resolved.relative_to(_ALLOWED_WRITE_ROOT)
    except ValueError as exc:
        payload = {{
            "path": str(resolved),
            "allowed_write_root": str(_ALLOWED_WRITE_ROOT),
        }}
        print({SANDBOX_WRITE_VIOLATION_MARKER!r} + json.dumps(payload, sort_keys=True), file=sys.stderr)
        raise _SandboxWriteViolation(
            f"Write path {{resolved}} is outside allowed root {{_ALLOWED_WRITE_ROOT}}."
        ) from exc
    return resolved


def _guarded_open(file, mode="r", *args, **kwargs):
    if _is_write_mode(mode):
        if not isinstance(file, (str, bytes, pathlib.Path)):
            raise _SandboxWriteViolation("Writing to file descriptors is not allowed in the sandbox.")
        _assert_write_allowed(file)
    return _ORIGINAL_OPEN(file, mode, *args, **kwargs)


def _guarded_io_open(file, mode="r", *args, **kwargs):
    if _is_write_mode(mode):
        if not isinstance(file, (str, bytes, pathlib.Path)):
            raise _SandboxWriteViolation("Writing to file descriptors is not allowed in the sandbox.")
        _assert_write_allowed(file)
    return _ORIGINAL_IO_OPEN(file, mode, *args, **kwargs)


def _guarded_path_open(self, mode="r", *args, **kwargs):
    if _is_write_mode(mode):
        _assert_write_allowed(self)
    return _ORIGINAL_PATH_OPEN(self, mode, *args, **kwargs)


def _guarded_write_text(self, *args, **kwargs):
    _assert_write_allowed(self)
    return _ORIGINAL_WRITE_TEXT(self, *args, **kwargs)


def _guarded_write_bytes(self, *args, **kwargs):
    _assert_write_allowed(self)
    return _ORIGINAL_WRITE_BYTES(self, *args, **kwargs)


def _guarded_touch(self, *args, **kwargs):
    _assert_write_allowed(self)
    return _ORIGINAL_TOUCH(self, *args, **kwargs)


def _guarded_mkdir(self, *args, **kwargs):
    _assert_write_allowed(self)
    return _ORIGINAL_MKDIR(self, *args, **kwargs)


def _guarded_unlink(self, *args, **kwargs):
    _assert_write_allowed(self)
    return _ORIGINAL_UNLINK(self, *args, **kwargs)


def _guarded_rmdir(self, *args, **kwargs):
    _assert_write_allowed(self)
    return _ORIGINAL_RMDIR(self, *args, **kwargs)


def _guarded_chmod(self, *args, **kwargs):
    _assert_write_allowed(self)
    return _ORIGINAL_CHMOD(self, *args, **kwargs)


def _guarded_rename(self, target, *args, **kwargs):
    _assert_write_allowed(self)
    _assert_write_allowed(target)
    return _ORIGINAL_RENAME(self, target, *args, **kwargs)


def _guarded_replace(self, target, *args, **kwargs):
    _assert_write_allowed(self)
    _assert_write_allowed(target)
    return _ORIGINAL_REPLACE(self, target, *args, **kwargs)


def _guarded_symlink_to(self, target, *args, **kwargs):
    _assert_write_allowed(self)
    _assert_write_allowed(target)
    return _ORIGINAL_SYMLINK_TO(self, target, *args, **kwargs)


def _guarded_hardlink_to(self, target, *args, **kwargs):
    _assert_write_allowed(self)
    _assert_write_allowed(target)
    return _ORIGINAL_HARDLINK_TO(self, target, *args, **kwargs)


_ORIGINAL_PATH_OPEN = pathlib.Path.open
_ORIGINAL_WRITE_TEXT = pathlib.Path.write_text
_ORIGINAL_WRITE_BYTES = pathlib.Path.write_bytes
_ORIGINAL_TOUCH = pathlib.Path.touch
_ORIGINAL_MKDIR = pathlib.Path.mkdir
_ORIGINAL_UNLINK = pathlib.Path.unlink
_ORIGINAL_RMDIR = pathlib.Path.rmdir
_ORIGINAL_CHMOD = pathlib.Path.chmod
_ORIGINAL_RENAME = pathlib.Path.rename
_ORIGINAL_REPLACE = pathlib.Path.replace
_ORIGINAL_SYMLINK_TO = pathlib.Path.symlink_to
_ORIGINAL_HARDLINK_TO = pathlib.Path.hardlink_to

builtins.open = _guarded_open
io.open = _guarded_io_open
pathlib.Path.open = _guarded_path_open
pathlib.Path.write_text = _guarded_write_text
pathlib.Path.write_bytes = _guarded_write_bytes
pathlib.Path.touch = _guarded_touch
pathlib.Path.mkdir = _guarded_mkdir
pathlib.Path.unlink = _guarded_unlink
pathlib.Path.rmdir = _guarded_rmdir
pathlib.Path.chmod = _guarded_chmod
pathlib.Path.rename = _guarded_rename
pathlib.Path.replace = _guarded_replace
pathlib.Path.symlink_to = _guarded_symlink_to
pathlib.Path.hardlink_to = _guarded_hardlink_to


def _patch_module(module_name):
    if module_name in _PATCHED_MODULES:
        return
    module = sys.modules.get(module_name)
    if module is None:
        return
    if module_name == "geopandas":
        frame_class = getattr(module, "GeoDataFrame", None)
        if frame_class is not None and hasattr(frame_class, "to_file"):
            original_to_file = frame_class.to_file

            def guarded_to_file(self, filename, *args, **kwargs):
                _assert_write_allowed(filename)
                return original_to_file(self, filename, *args, **kwargs)

            frame_class.to_file = guarded_to_file
    elif module_name in {{"fiona", "rasterio"}} and hasattr(module, "open"):
        original_open = module.open

        def guarded_module_open(path, mode="r", *args, **kwargs):
            if _is_write_mode(mode):
                _assert_write_allowed(path)
            return original_open(path, mode, *args, **kwargs)

        module.open = guarded_module_open
    _PATCHED_MODULES.add(module_name)


def _guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
    module = _ORIGINAL_IMPORT(name, globals, locals, fromlist, level)
    root = name.split(".", 1)[0]
    for module_name in (root, name):
        _patch_module(module_name)
    return module


builtins.__import__ = _guarded_import

try:
    runpy.run_path(str(_SCRIPT_PATH), run_name="__main__")
except _SandboxWriteViolation:
    sys.exit({SANDBOX_WRITE_VIOLATION_CODE})
"""

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
            if item.code in {"import_not_allowed", "import_not_whitelisted"}
        ]
        blocked_calls = [
            item.details.get("name", item.message)
            for item in report.observations
            if item.code in {"call_not_allowed", "dangerous_call"}
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

    def _write_violation_observations(self, stderr: str) -> list[Observation]:
        observations: list[Observation] = []
        for line in stderr.splitlines():
            if not line.startswith(SANDBOX_WRITE_VIOLATION_MARKER):
                continue
            raw_payload = line.removeprefix(SANDBOX_WRITE_VIOLATION_MARKER)
            try:
                details = json.loads(raw_payload)
            except json.JSONDecodeError:
                details = {
                    "path": None,
                    "allowed_write_root": str(self.write_root.resolve()),
                    "raw": raw_payload,
                }
            observations.append(
                Observation(
                    code="sandbox_write_outside_root",
                    message=(
                        f"Sandbox blocked a write outside the allowed root: {details.get('path')}"
                    ),
                    suggested_fix="Write generated artifacts under the configured sandbox artifact directory.",
                    details=details,
                )
            )
        return observations

    def run_python(
        self,
        script_text: str,
        *,
        run_id: str,
        step_name: str,
        expected_output_path: str | Path | None = None,
    ) -> SandboxResult:
        ensure_run_dirs(self.run_root)
        self.write_root.mkdir(parents=True, exist_ok=True)
        report: GuardrailReport = validate_python_script(script_text)
        risk_preview = self.preview_script_risk(script_text)
        log_dir = self.run_root / "logs" / run_id
        log_dir.mkdir(parents=True, exist_ok=True)
        script_path = log_dir / f"{step_name}.py"
        script_path.write_text(script_text, encoding="utf-8")
        resolved_script_path = script_path.resolve()
        wrapper_path = log_dir / f"{step_name}-sandbox.py"
        wrapper_path.write_text(self._build_runtime_wrapper(resolved_script_path), encoding="utf-8")
        resolved_wrapper_path = wrapper_path.resolve()

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
                command=[sys.executable, str(resolved_wrapper_path)],
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
                command=[sys.executable, str(resolved_wrapper_path)],
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

        command = [sys.executable, str(resolved_wrapper_path)]
        started = time.perf_counter()
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                cwd=self.working_directory,
                check=False,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            )
            duration = time.perf_counter() - started
            write_observations = self._write_violation_observations(completed.stderr)
            result = SandboxResult(
                script_path=str(resolved_script_path),
                command=command,
                returncode=completed.returncode if not write_observations else 1,
                stdout=completed.stdout,
                stderr=completed.stderr,
                timed_out=False,
                duration_seconds=duration,
                blocked_by_guardrails=bool(write_observations),
                observations=write_observations,
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
