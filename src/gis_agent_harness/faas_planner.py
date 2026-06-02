from __future__ import annotations

from typing import Any

from .resource_router import ResourceRoute


def build_faas_manifest(
    *,
    function_name: str,
    image: str,
    handler: str,
    input_assets: list[str],
    resource_route: ResourceRoute,
) -> dict[str, Any]:
    return {
        "function_name": function_name,
        "mode": "manifest-only",
        "orchestration": "serverless-faas",
        "image": image,
        "handler": handler,
        "input_assets": input_assets,
        "resource_route": resource_route.to_dict(),
        "network_required": False,
    }
