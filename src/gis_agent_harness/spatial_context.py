from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .spatial_tools import inspect_raster, inspect_vector

VECTOR_SUFFIXES = {".gpkg", ".shp", ".geojson", ".json"}
RASTER_SUFFIXES = {".tif", ".tiff"}
DEFAULT_EXCLUDE_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".runs",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "reports",
}


@dataclass(slots=True)
class SpatialDatasetSummary:
    path: str
    kind: str
    driver: str | None = None
    crs: str | None = None
    bounds: list[float] | None = None
    geometry_type: str | None = None
    feature_count: int | None = None
    schema: dict[str, Any] = field(default_factory=dict)
    raster: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SpatialRepoMap:
    root: str
    datasets: list[SpatialDatasetSummary]
    skipped_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "root": self.root,
            "dataset_count": len(self.datasets),
            "skipped_count": self.skipped_count,
            "datasets": [dataset.to_dict() for dataset in self.datasets],
        }


def is_spatial_dataset(path: str | Path) -> bool:
    suffix = Path(path).suffix.lower()
    return suffix in VECTOR_SUFFIXES or suffix in RASTER_SUFFIXES


def _iter_spatial_paths(root: Path, exclude_dirs: set[str]) -> list[Path]:
    paths: list[Path] = []
    for candidate in root.rglob("*"):
        if not candidate.is_file():
            continue
        if any(part in exclude_dirs for part in candidate.relative_to(root).parts[:-1]):
            continue
        if is_spatial_dataset(candidate):
            paths.append(candidate)
    return sorted(paths)


def _relative(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _summarize_vector(path: Path, root: Path) -> SpatialDatasetSummary:
    try:
        info = inspect_vector(path, sample_size=0)
        schema = dict(info.schema or {})
        return SpatialDatasetSummary(
            path=_relative(path, root),
            kind="vector",
            driver=info.driver,
            crs=info.crs,
            bounds=info.bounds,
            geometry_type=schema.get("geometry"),
            feature_count=info.feature_count,
            schema=dict(schema.get("properties") or {}),
        )
    except Exception as exc:
        return SpatialDatasetSummary(path=_relative(path, root), kind="vector", error=str(exc))


def _summarize_raster(path: Path, root: Path) -> SpatialDatasetSummary:
    try:
        info = inspect_raster(path)
        return SpatialDatasetSummary(
            path=_relative(path, root),
            kind="raster",
            driver=info.driver,
            crs=info.crs,
            bounds=info.bounds,
            raster={
                "width": info.width,
                "height": info.height,
                "band_count": info.count,
                "indexes": info.indexes,
                "dtypes": info.dtypes,
                "nodatavals": info.nodatavals,
                "transform": info.transform,
            },
        )
    except Exception as exc:
        return SpatialDatasetSummary(path=_relative(path, root), kind="raster", error=str(exc))


def build_spatial_repo_map(
    root: str | Path,
    *,
    max_datasets: int = 50,
    exclude_dirs: set[str] | None = None,
) -> SpatialRepoMap:
    root_path = Path(root).resolve()
    if not root_path.exists():
        raise FileNotFoundError(f"Spatial map root does not exist: {root_path}")
    if not root_path.is_dir():
        raise NotADirectoryError(f"Spatial map root must be a directory: {root_path}")

    excluded = set(DEFAULT_EXCLUDE_DIRS)
    if exclude_dirs:
        excluded.update(exclude_dirs)

    spatial_paths = _iter_spatial_paths(root_path, excluded)
    selected_paths = spatial_paths[:max_datasets]
    datasets: list[SpatialDatasetSummary] = []
    for path in selected_paths:
        suffix = path.suffix.lower()
        if suffix in VECTOR_SUFFIXES:
            datasets.append(_summarize_vector(path, root_path))
        elif suffix in RASTER_SUFFIXES:
            datasets.append(_summarize_raster(path, root_path))

    return SpatialRepoMap(
        root=str(root_path),
        datasets=datasets,
        skipped_count=max(0, len(spatial_paths) - len(selected_paths)),
    )
