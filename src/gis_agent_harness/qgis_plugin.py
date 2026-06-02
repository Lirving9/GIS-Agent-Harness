from __future__ import annotations

from typing import Any


def build_qgis_plugin_manifest(plugin_name: str = "GISAgentMCPBridge") -> dict[str, Any]:
    return {
        "plugin_name": plugin_name,
        "transport": "mcp-json-rpc",
        "mode": "desktop-bridge-manifest",
        "capabilities": [
            "layer_tree_control",
            "qml_style_application",
            "layout_export",
            "qgis_process_preview",
        ],
        "approval_required": True,
        "network_required": False,
    }
