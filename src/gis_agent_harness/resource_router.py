from __future__ import annotations

import ast
from dataclasses import dataclass, field
from typing import Any


GPU_IMPORT_ROOTS = {"cupy", "jax", "tensorflow", "torch", "torchvision"}
RASTER_IMPORT_ROOTS = {"rasterio", "xarray"}


@dataclass(slots=True)
class ResourceRoute:
    track: str
    hardware: str
    container_profile: str
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "track": self.track,
            "hardware": self.hardware,
            "container_profile": self.container_profile,
            "reasons": self.reasons,
        }


def _import_roots(script_text: str) -> set[str]:
    try:
        tree = ast.parse(script_text)
    except SyntaxError:
        return set()
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".", 1)[0])
    return roots


def route_code(script_text: str) -> ResourceRoute:
    roots = _import_roots(script_text)
    gpu_hits = sorted(roots & GPU_IMPORT_ROOTS)
    if gpu_hits:
        return ResourceRoute(
            track="gpu",
            hardware="cuda-capable-gpu",
            container_profile="geoai-gpu",
            reasons=[f"Detected GPU-oriented import: {name}" for name in gpu_hits],
        )
    raster_hits = sorted(roots & RASTER_IMPORT_ROOTS)
    if raster_hits:
        return ResourceRoute(
            track="cpu",
            hardware="cpu-high-memory",
            container_profile="geoai-raster-cpu",
            reasons=[f"Detected raster workload import: {name}" for name in raster_hits],
        )
    return ResourceRoute(
        track="cpu",
        hardware="cpu-standard",
        container_profile="geoai-vector-cpu",
        reasons=["No GPU-oriented imports detected."],
    )
