from __future__ import annotations

from pathlib import Path


def generate_sample_data(base_dir: str | Path) -> dict[str, str]:
    base_path = Path(base_dir)
    vector_dir = base_path / "vector"
    raster_dir = base_path / "raster"
    vector_dir.mkdir(parents=True, exist_ok=True)
    raster_dir.mkdir(parents=True, exist_ok=True)

    import geopandas as gpd
    import numpy as np
    import rasterio
    from rasterio.transform import from_origin
    from shapely.geometry import Polygon, box

    from .spatial_tools import remove_existing_vector

    valid = gpd.GeoDataFrame(
        {
            "name": ["parcel_a", "parcel_b"],
            "value": [1, 2],
        },
        geometry=[
            box(-0.75, -0.75, -0.25, -0.25),
            box(-0.1, -0.5, 0.4, 0.1),
        ],
        crs="EPSG:4326",
    )
    valid_3857 = valid.to_crs("EPSG:3857")
    invalid = gpd.GeoDataFrame(
        {"name": ["bowtie"], "value": [99]},
        geometry=[
            Polygon(
                [
                    (-0.6, -0.6),
                    (0.2, 0.2),
                    (-0.6, 0.2),
                    (0.2, -0.6),
                    (-0.6, -0.6),
                ]
            )
        ],
        crs="EPSG:4326",
    )

    sample_gpkg = vector_dir / "sample.gpkg"
    sample_shp = vector_dir / "sample.shp"
    sample_3857 = vector_dir / "sample_3857.gpkg"
    invalid_path = vector_dir / "invalid_geometry.gpkg"
    missing_crs = vector_dir / "missing_crs.shp"

    for path in (sample_gpkg, sample_shp, sample_3857, invalid_path, missing_crs):
        remove_existing_vector(path)

    valid.to_file(sample_gpkg, driver="GPKG")
    valid.to_file(sample_shp, driver="ESRI Shapefile")
    valid_3857.to_file(sample_3857, driver="GPKG")
    invalid.to_file(invalid_path, driver="GPKG")
    valid.to_file(missing_crs, driver="ESRI Shapefile")
    (missing_crs.with_suffix(".prj")).unlink(missing_ok=True)

    raster_path = raster_dir / "sample.tif"
    raster_path.unlink(missing_ok=True)
    data = np.arange(64, dtype="float32").reshape((8, 8))
    transform = from_origin(-1.0, 1.0, 0.25, 0.25)
    with rasterio.open(
        raster_path,
        "w",
        driver="GTiff",
        width=8,
        height=8,
        count=1,
        dtype="float32",
        crs="EPSG:4326",
        transform=transform,
        nodata=-9999.0,
    ) as dst:
        dst.write(data, 1)

    return {
        "sample_gpkg": str(sample_gpkg),
        "sample_shp": str(sample_shp),
        "sample_3857": str(sample_3857),
        "invalid_geometry": str(invalid_path),
        "missing_crs": str(missing_crs),
        "sample_raster": str(raster_path),
    }
