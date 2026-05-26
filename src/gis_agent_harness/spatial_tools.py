from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .errors import DataInspectionError


@dataclass(slots=True)
class VectorInspection:
    path: str
    driver: str | None
    crs: str | None
    bounds: list[float] | None
    schema: dict[str, Any]
    feature_count: int | None
    sample_records: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class RasterInspection:
    path: str
    driver: str | None
    crs: str | None
    bounds: list[float] | None
    width: int
    height: int
    count: int
    indexes: list[int]
    dtypes: list[str]
    nodatavals: list[float | int | None]
    transform: list[float]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _normalize_crs(value: Any) -> str | None:
    if value is None:
        return None
    try:
        from pyproj import CRS

        return CRS.from_user_input(value).to_string()
    except Exception:
        text = str(value)
        return text or None


def infer_vector_driver(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".gpkg":
        return "GPKG"
    if suffix == ".shp":
        return "ESRI Shapefile"
    if suffix in {".json", ".geojson"}:
        return "GeoJSON"
    raise DataInspectionError(f"Unsupported vector output format: {path.suffix}")


def remove_existing_vector(path: Path) -> None:
    if path.suffix.lower() == ".shp":
        for sibling in path.parent.glob(f"{path.stem}.*"):
            sibling.unlink(missing_ok=True)
        return
    if path.suffix.lower() == ".gpkg":
        for sibling in path.parent.glob(f"{path.name}*"):
            sibling.unlink(missing_ok=True)
        return
    path.unlink(missing_ok=True)


def inspect_vector(path: str | Path, sample_size: int = 3) -> VectorInspection:
    vector_path = Path(path)
    if not vector_path.exists():
        raise DataInspectionError(f"Vector dataset not found: {vector_path}")

    try:
        import fiona
    except ImportError as exc:
        raise DataInspectionError("Fiona is required for vector inspection") from exc

    try:
        with fiona.open(vector_path) as src:
            sample_records: list[dict[str, Any]] = []
            for index, feature in enumerate(src):
                if index >= sample_size:
                    break
                sample_records.append(
                    {
                        "id": feature.get("id"),
                        "properties": dict(feature.get("properties") or {}),
                        "geometry_type": (feature.get("geometry") or {}).get("type"),
                    }
                )

            return VectorInspection(
                path=str(vector_path),
                driver=getattr(src, "driver", None),
                crs=_normalize_crs(src.crs_wkt or src.crs),
                bounds=list(src.bounds) if src.bounds else None,
                schema=dict(src.schema or {}),
                feature_count=len(src),
                sample_records=sample_records,
            )
    except Exception as exc:
        raise DataInspectionError(f"Failed to inspect vector dataset {vector_path}: {exc}") from exc


def inspect_raster(path: str | Path) -> RasterInspection:
    raster_path = Path(path)
    if not raster_path.exists():
        raise DataInspectionError(f"Raster dataset not found: {raster_path}")

    try:
        import rasterio
    except ImportError as exc:
        raise DataInspectionError("Rasterio is required for raster inspection") from exc

    try:
        with rasterio.open(raster_path) as src:
            transform = list(src.transform)[:6]
            return RasterInspection(
                path=str(raster_path),
                driver=getattr(src, "driver", None),
                crs=_normalize_crs(src.crs),
                bounds=[src.bounds.left, src.bounds.bottom, src.bounds.right, src.bounds.top],
                width=src.width,
                height=src.height,
                count=src.count,
                indexes=list(src.indexes),
                dtypes=list(src.dtypes),
                nodatavals=list(src.nodatavals),
                transform=transform,
            )
    except Exception as exc:
        raise DataInspectionError(f"Failed to inspect raster dataset {raster_path}: {exc}") from exc


def read_vector_frame(path: str | Path):
    vector_path = Path(path)
    if not vector_path.exists():
        raise DataInspectionError(f"Vector dataset not found: {vector_path}")

    try:
        import geopandas as gpd
    except ImportError as exc:
        raise DataInspectionError("GeoPandas is required for vector operations") from exc

    try:
        return gpd.read_file(vector_path)
    except Exception as exc:
        raise DataInspectionError(f"Failed to read vector dataset {vector_path}: {exc}") from exc


def write_vector_frame(frame, path: str | Path) -> Path:
    vector_path = Path(path)
    vector_path.parent.mkdir(parents=True, exist_ok=True)
    remove_existing_vector(vector_path)
    driver = infer_vector_driver(vector_path)
    frame.to_file(vector_path, driver=driver)
    return vector_path


def transform_bounds(bounds: list[float], source_crs: str, target_crs: str) -> list[float]:
    try:
        from rasterio.warp import transform_bounds as rio_transform_bounds
    except ImportError as exc:
        raise DataInspectionError("Rasterio is required for bounds transforms") from exc

    left, bottom, right, top = bounds
    result = rio_transform_bounds(source_crs, target_crs, left, bottom, right, top)
    return [result[0], result[1], result[2], result[3]]
