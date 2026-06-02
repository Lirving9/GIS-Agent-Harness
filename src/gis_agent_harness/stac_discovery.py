from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class STACQueryPlan:
    endpoint: str
    query: dict[str, Any]
    network_required: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "endpoint": self.endpoint,
            "query": self.query,
            "network_required": self.network_required,
        }


def build_stac_query_plan(
    *,
    collections: list[str],
    bbox: list[float],
    datetime_range: str,
    max_cloud_cover: float | None = None,
    endpoint: str = "https://planetarycomputer.microsoft.com/api/stac/v1/search",
) -> STACQueryPlan:
    if len(bbox) != 4:
        raise ValueError("STAC bbox must contain exactly four numeric values.")
    query: dict[str, Any] = {
        "collections": collections,
        "bbox": [float(value) for value in bbox],
        "datetime": datetime_range,
        "limit": 100,
        "query": {},
    }
    if max_cloud_cover is not None:
        query["query"]["eo:cloud_cover"] = {"lt": max_cloud_cover}
    return STACQueryPlan(endpoint=endpoint, query=query, network_required=False)
