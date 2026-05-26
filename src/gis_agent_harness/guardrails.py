from __future__ import annotations

import ast
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .errors import Observation
from .spatial_tools import inspect_raster, inspect_vector, read_vector_frame

SAFE_IMPORT_ROOTS = {
    "collections",
    "fiona",
    "geopandas",
    "json",
    "math",
    "numpy",
    "pathlib",
    "pyproj",
    "rasterio",
    "shapely",
}
DISALLOWED_IMPORT_ROOTS = {
    "httpx",
    "os",
    "requests",
    "shutil",
    "socket",
    "subprocess",
    "urllib",
}
DISALLOWED_CALL_NAMES = {"__import__", "compile", "eval", "exec"}


@dataclass(slots=True)
class GuardrailReport:
    allowed: bool
    observations: list[Observation]

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "observations": [asdict(item) for item in self.observations],
        }


class ScriptPolicyVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.import_aliases: dict[str, str] = {}
        self.observations: list[Observation] = []

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            root = alias.name.split(".")[0]
            self.import_aliases[alias.asname or root] = alias.name
            if root in DISALLOWED_IMPORT_ROOTS:
                self.observations.append(
                    Observation(
                        code="import_not_allowed",
                        message=f"Import blocked: {alias.name}",
                        suggested_fix="Remove network, OS, and subprocess imports from generated code.",
                    )
                )
            elif root not in SAFE_IMPORT_ROOTS:
                self.observations.append(
                    Observation(
                        code="import_not_whitelisted",
                        message=f"Import not in whitelist: {alias.name}",
                        suggested_fix="Restrict generated code to GIS and safe standard-library modules.",
                    )
                )
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        root = module.split(".")[0]
        for alias in node.names:
            self.import_aliases[alias.asname or alias.name] = f"{module}.{alias.name}".strip(".")
        if root in DISALLOWED_IMPORT_ROOTS:
            self.observations.append(
                Observation(
                    code="import_not_allowed",
                    message=f"Import blocked: {module}",
                    suggested_fix="Remove network, OS, and subprocess imports from generated code.",
                )
            )
        elif root not in SAFE_IMPORT_ROOTS:
            self.observations.append(
                Observation(
                    code="import_not_whitelisted",
                    message=f"Import not in whitelist: {module}",
                    suggested_fix="Restrict generated code to GIS and safe standard-library modules.",
                )
            )
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Name):
            target = self.import_aliases.get(node.func.id, node.func.id)
            root = target.split(".")[0]
            if node.func.id in DISALLOWED_CALL_NAMES:
                self.observations.append(
                    Observation(
                        code="dangerous_call",
                        message=f"Call blocked: {node.func.id}",
                        suggested_fix="Avoid dynamic execution helpers in generated code.",
                    )
                )
            if root in DISALLOWED_IMPORT_ROOTS:
                self.observations.append(
                    Observation(
                        code="dangerous_call",
                        message=f"Call blocked: {target}",
                        suggested_fix="Use the harness sandbox instead of subprocess or OS shell calls.",
                    )
                )

        if isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name):
                base_name = node.func.value.id
                target = self.import_aliases.get(base_name, base_name)
                root = target.split(".")[0]
                if root in DISALLOWED_IMPORT_ROOTS:
                    self.observations.append(
                        Observation(
                            code="dangerous_call",
                            message=f"Call blocked: {target}.{node.func.attr}",
                            suggested_fix="Use GeoPandas, Fiona, and Rasterio APIs without shell access.",
                        )
                    )
        self.generic_visit(node)


def validate_python_script(script_text: str) -> GuardrailReport:
    try:
        tree = ast.parse(script_text)
    except SyntaxError as exc:
        return GuardrailReport(
            allowed=False,
            observations=[
                Observation(
                    code="syntax_error",
                    message=f"Generated Python failed to parse: {exc}",
                    suggested_fix="Return valid Python syntax before execution.",
                )
            ],
        )

    visitor = ScriptPolicyVisitor()
    visitor.visit(tree)
    return GuardrailReport(allowed=not visitor.observations, observations=visitor.observations)


def _make_observation(code: str, message: str, suggested_fix: str | None = None, **details: Any) -> Observation:
    return Observation(code=code, message=message, suggested_fix=suggested_fix, details=details)


def preflight_dataset_checks(
    vector_path: str | Path,
    raster_path: str | Path | None = None,
    *,
    check_geometry: bool = True,
) -> list[Observation]:
    observations: list[Observation] = []

    try:
        vector_info = inspect_vector(vector_path)
    except Exception as exc:
        return [
            _make_observation(
                "vector_inspection_failed",
                str(exc),
                suggested_fix="Verify the vector path and dataset integrity.",
            )
        ]

    if not vector_info.crs:
        observations.append(
            _make_observation(
                "missing_crs",
                f"Vector dataset has no CRS metadata: {vector_info.path}",
                suggested_fix="Use GeoDataFrame.set_crs(...) only to declare the existing source CRS before any reprojection.",
                dataset=vector_info.path,
            )
        )

    raster_info = None
    if raster_path is not None:
        try:
            raster_info = inspect_raster(raster_path)
        except Exception as exc:
            observations.append(
                _make_observation(
                    "raster_inspection_failed",
                    str(exc),
                    suggested_fix="Verify the raster path and dataset integrity.",
                )
            )
            raster_info = None

    if raster_info is not None and not raster_info.crs:
        observations.append(
            _make_observation(
                "missing_crs",
                f"Raster dataset has no CRS metadata: {raster_info.path}",
                suggested_fix="Repair the raster metadata before spatial alignment.",
                dataset=raster_info.path,
            )
        )

    if raster_info is not None and vector_info.crs and raster_info.crs and vector_info.crs != raster_info.crs:
        observations.append(
            _make_observation(
                "crs_mismatch",
                f"Vector CRS {vector_info.crs} does not match raster CRS {raster_info.crs}.",
                suggested_fix="Use GeoDataFrame.to_crs(...) to reproject the vector into the raster CRS before overlay or clip.",
                vector_crs=vector_info.crs,
                raster_crs=raster_info.crs,
            )
        )

    if check_geometry:
        frame = read_vector_frame(vector_info.path)
        validity = frame.geometry.is_valid.fillna(True)
        if not bool(validity.all()):
            invalid_count = int((~validity).sum())
            observations.append(
                _make_observation(
                    "invalid_geometry",
                    f"Vector dataset contains {invalid_count} invalid geometries.",
                    suggested_fix="Repair the geometry with GeoSeries.make_valid() before spatial analysis.",
                    invalid_count=invalid_count,
                )
            )

    return observations
