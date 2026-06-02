from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class MCPToolSpec:
    name: str
    domain: str
    description: str
    input_schema: dict[str, Any] = field(default_factory=dict)
    output_schema: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class MCPManifest:
    protocol: str
    server: str
    progressive_disclosure: bool
    tools: list[MCPToolSpec]

    def to_dict(self) -> dict[str, Any]:
        return {
            "protocol": self.protocol,
            "server": self.server,
            "progressive_disclosure": self.progressive_disclosure,
            "tools": [tool.to_dict() for tool in self.tools],
        }


TOOL_REGISTRY = [
    MCPToolSpec(
        name="inspect_vector",
        domain="vector",
        description="Inspect vector driver, CRS, bounds, schema, and feature count.",
        input_schema={"path": "string", "sample_size": "integer"},
        output_schema={"driver": "string", "crs": "string|null", "bounds": "array"},
    ),
    MCPToolSpec(
        name="repair_invalid_geometry",
        domain="vector",
        description="Repair invalid geometries with deterministic Shapely/GeoPandas operations.",
        input_schema={"vector_path": "string", "output_path": "string"},
        output_schema={"output_vector_path": "string", "invalid_count": "integer"},
    ),
    MCPToolSpec(
        name="inspect_raster",
        domain="raster",
        description="Inspect raster shape, bands, CRS, bounds, transform, and nodata values.",
        input_schema={"path": "string"},
        output_schema={"width": "integer", "height": "integer", "crs": "string|null"},
    ),
    MCPToolSpec(
        name="align_vector_to_raster",
        domain="raster",
        description="Plan a vector reprojection into a reference raster CRS.",
        input_schema={"vector_path": "string", "raster_path": "string"},
        output_schema={"output_vector_path": "string", "target_crs": "string"},
    ),
    MCPToolSpec(
        name="stac_query_plan",
        domain="discovery",
        description="Build a dry-run STAC search request for spatiotemporal asset discovery.",
        input_schema={"collections": "array", "bbox": "array", "datetime": "string"},
        output_schema={"query": "object", "network_required": "boolean"},
    ),
    MCPToolSpec(
        name="qgis_process_preview",
        domain="desktop",
        description="Preview qgis_process JSON payloads behind a local approval gate.",
        input_schema={"algorithm": "string", "parameters": "object"},
        output_schema={"command": "array", "risk": "object"},
    ),
]


def build_mcp_manifest(domain: str | None = None) -> MCPManifest:
    selected = [tool for tool in TOOL_REGISTRY if domain is None or tool.domain == domain]
    return MCPManifest(
        protocol="mcp-json-rpc",
        server="gis-agent-harness-local",
        progressive_disclosure=True,
        tools=selected,
    )
