from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


@dataclass(slots=True)
class MCPToolResult:
    tool_name: str
    success: bool
    payload: dict[str, Any]
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "success": self.success,
            "payload": self.payload,
            "error": self.error,
        }


def _inspect_vector(params: dict[str, Any]) -> dict[str, Any]:
    from .spatial_tools import inspect_vector

    path = params.get("path")
    if not path:
        raise ValueError("inspect_vector requires path.")
    sample_size = int(params.get("sample_size", 3))
    return inspect_vector(Path(path), sample_size=sample_size).to_dict()


def _inspect_raster(params: dict[str, Any]) -> dict[str, Any]:
    from .spatial_tools import inspect_raster

    path = params.get("path")
    if not path:
        raise ValueError("inspect_raster requires path.")
    return inspect_raster(Path(path)).to_dict()


def _write_text(params: dict[str, Any]) -> dict[str, Any]:
    path = Path(str(params.get("path", "")))
    if not path:
        raise ValueError("write_text requires path.")
    text = str(params.get("text", ""))
    append = bool(params.get("append", False))
    path.parent.mkdir(parents=True, exist_ok=True)
    if append:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(text)
    else:
        path.write_text(text, encoding="utf-8")
    return {"path": str(path), "bytes": len(text.encode("utf-8")), "append": append}


TOOL_HANDLERS: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "inspect_vector": _inspect_vector,
    "inspect_raster": _inspect_raster,
    "write_text": _write_text,
}


def call_mcp_tool(tool_name: str, parameters: dict[str, Any]) -> MCPToolResult:
    normalized_name = tool_name.replace("-", "_")
    handler = TOOL_HANDLERS.get(normalized_name)
    if handler is None:
        return MCPToolResult(
            tool_name=tool_name,
            success=False,
            payload={},
            error=f"Unknown MCP tool: {tool_name}",
        )
    try:
        return MCPToolResult(tool_name=normalized_name, success=True, payload=handler(parameters))
    except Exception as exc:
        return MCPToolResult(tool_name=normalized_name, success=False, payload={}, error=str(exc))
