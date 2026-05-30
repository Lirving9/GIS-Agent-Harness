from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .errors import HarnessError

ALGORITHM_ID_PATTERN = re.compile(r"^[A-Za-z0-9_]+:[A-Za-z0-9_.-]+$")


class QGISProcessError(HarnessError):
    """Raised when a qgis_process request cannot be prepared or executed."""


@dataclass(slots=True)
class QGISProcessRequest:
    algorithm: str
    parameters: dict[str, Any]
    qgis_process_path: str = "qgis_process"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class QGISProcessResult:
    algorithm: str
    command: list[str]
    parameters: dict[str, Any]
    dry_run: bool
    confirmed: bool = False
    approval_required: bool = False
    returncode: int | None = None
    stdout: str = ""
    stderr: str = ""
    executable_found: bool = False
    risk: dict[str, Any] = field(default_factory=dict)
    observations: list[dict[str, Any]] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return self.returncode == 0 if self.returncode is not None else self.dry_run

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["success"] = self.success
        return payload


def validate_algorithm_id(algorithm: str) -> None:
    if not ALGORITHM_ID_PATTERN.match(algorithm):
        raise QGISProcessError(
            "qgis_process algorithm ids must look like 'provider:algorithm' and contain only safe characters."
        )


def load_payload(path: str | Path | None = None, payload_json: str | None = None) -> dict[str, Any]:
    if path is not None and payload_json is not None:
        raise QGISProcessError("Use either a payload file or inline JSON, not both.")
    if path is None and payload_json is None:
        return {}

    raw = Path(path).read_text(encoding="utf-8") if path is not None else str(payload_json)
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise QGISProcessError(f"Payload is not valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise QGISProcessError("qgis_process payload must be a JSON object.")
    return payload


def run_qgis_process(
    request: QGISProcessRequest,
    *,
    dry_run: bool = False,
    timeout_seconds: int = 120,
    confirmed: bool = False,
) -> QGISProcessResult:
    validate_algorithm_id(request.algorithm)
    command = [request.qgis_process_path, "run", request.algorithm, "-"]
    executable = shutil.which(request.qgis_process_path)
    serialized_parameters = json.dumps(request.parameters, ensure_ascii=False)
    result = QGISProcessResult(
        algorithm=request.algorithm,
        command=command,
        parameters=request.parameters,
        dry_run=dry_run,
        confirmed=confirmed,
        executable_found=executable is not None,
        risk={
            "payload_bytes": len(serialized_parameters.encode("utf-8")),
            "parameter_count": _count_parameters(request.parameters),
            "input_paths": _extract_input_paths(request.parameters),
        },
    )
    if dry_run:
        return result
    if not confirmed:
        result.returncode = 1
        result.approval_required = True
        result.stderr = "qgis_process execution requires explicit confirmation."
        result.observations.append(
            {
                "code": "qgis_process_confirmation_required",
                "message": result.stderr,
                "suggested_fix": "Re-run with --confirm after reviewing the payload and risk summary.",
            }
        )
        return result
    if executable is None:
        result.returncode = 127
        result.stderr = f"Executable not found: {request.qgis_process_path}"
        result.observations.append(
            {
                "code": "qgis_process_not_found",
                "message": result.stderr,
                "suggested_fix": "Install QGIS or pass --qgis-process-path pointing to qgis_process.",
            }
        )
        return result

    command = [executable, "run", request.algorithm, "-"]
    try:
        completed = subprocess.run(
            command,
            input=serialized_parameters,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        result.command = command
        result.returncode = 124
        result.stdout = exc.stdout or ""
        result.stderr = exc.stderr or ""
        result.observations.append(
            {
                "code": "qgis_process_timeout",
                "message": f"qgis_process exceeded {timeout_seconds} second(s).",
                "suggested_fix": "Reduce input size, simplify the algorithm, or increase --timeout.",
            }
        )
        return result

    result.command = command
    result.returncode = completed.returncode
    result.stdout = completed.stdout
    result.stderr = completed.stderr
    if completed.returncode != 0:
        result.observations.append(
            {
                "code": "qgis_process_failed",
                "message": completed.stderr.strip() or completed.stdout.strip() or "qgis_process returned non-zero status.",
                "suggested_fix": "Inspect algorithm id, JSON parameters, CRS, and local QGIS installation.",
            }
        )
    return result


def _count_parameters(payload: Any) -> int:
    if isinstance(payload, dict):
        return len(payload) + sum(_count_parameters(value) for value in payload.values())
    if isinstance(payload, list):
        return sum(_count_parameters(value) for value in payload)
    return 0


def _extract_input_paths(payload: Any) -> list[str]:
    paths: list[str] = []
    if isinstance(payload, dict):
        for value in payload.values():
            paths.extend(_extract_input_paths(value))
    elif isinstance(payload, list):
        for value in payload:
            paths.extend(_extract_input_paths(value))
    elif isinstance(payload, str):
        if Path(payload).suffix.lower() in {".gpkg", ".shp", ".geojson", ".json", ".tif", ".tiff"}:
            paths.append(payload)
    return sorted(set(paths))
