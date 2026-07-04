"""McpToolAdapter — converts McpToolInfo into (ToolSpec, ToolHandler) pairs."""

from __future__ import annotations

from typing import Any

from ..tools.contracts import ToolExecutionContext, ToolHandler, ToolResult, ToolSpec
from .client import McpClientManager
from .contracts import McpServerConfig, McpToolInfo


# ---------------------------------------------------------------------------
# Internal ToolHandler implementation
# ---------------------------------------------------------------------------


class _McpToolHandler:
    """ToolHandler that forwards execution to a remote MCP server tool."""

    def __init__(
        self,
        client_manager: McpClientManager,
        server_name: str,
        remote_tool_name: str,
    ) -> None:
        self._manager = client_manager
        self._server_name = server_name
        self._remote_tool_name = remote_tool_name

    async def execute(
        self,
        arguments: dict[str, Any],
        context: ToolExecutionContext,
    ) -> ToolResult:
        try:
            output = await self._manager.call_tool(
                self._server_name,
                self._remote_tool_name,
                arguments,
            )
            return ToolResult(output=output, status="success")
        except Exception as exc:  # noqa: BLE001
            return ToolResult(
                output="",
                status="error",
                error_message=str(exc),
            )


# ---------------------------------------------------------------------------
# McpToolAdapter
# ---------------------------------------------------------------------------


class McpToolAdapter:
    """Converts :class:`McpToolInfo` objects into ``(ToolSpec, ToolHandler)`` pairs.

    The resulting ToolSpec carries:
    - The tool name, optionally prefixed by ``config.tool_name_prefix``.
    - Tags ``{"mcp", "mcp:<server_name>"}`` merged with any server-level tags.
    - The server's ``timeout_seconds``.
    """

    def __init__(self, client_manager: McpClientManager) -> None:
        self._manager = client_manager

    def adapt(
        self,
        tool_info: McpToolInfo,
        config: McpServerConfig,
    ) -> tuple[ToolSpec, ToolHandler]:
        """Produce a ``(ToolSpec, ToolHandler)`` for *tool_info*.

        Args:
            tool_info: Metadata from the MCP server.
            config: Server configuration (used for prefix, tags, timeout).

        Returns:
            A tuple ``(spec, handler)`` ready for registry insertion.
        """
        tool_name = (
            f"{config.tool_name_prefix}{tool_info.name}"
            if config.tool_name_prefix
            else tool_info.name
        )
        mcp_tags = frozenset({"mcp", f"mcp:{config.name}"})
        all_tags = config.tags | mcp_tags

        spec = ToolSpec(
            name=tool_name,
            description=tool_info.description,
            parameters_schema=tool_info.input_schema,
            tags=all_tags,
            timeout_seconds=config.timeout_seconds,
        )
        handler: ToolHandler = _McpToolHandler(
            client_manager=self._manager,
            server_name=tool_info.server_name,
            remote_tool_name=tool_info.name,
        )
        return spec, handler
