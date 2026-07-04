"""MCP transport adapter — wraps the standard ``mcp`` SDK transports.

Provides a unified async-context-manager interface over ``mcp`` SDK's
``ClientSession`` + transport layer (stdio / SSE / streamable-HTTP).
Replaces the previous ``pydantic_ai.mcp`` dependency.
"""

from __future__ import annotations

import logging
from contextlib import AsyncExitStack
from typing import Any

from mcp import ClientSession
from mcp.types import CallToolResult, TextContent, Tool

from .contracts import McpServerConfig

logger = logging.getLogger(__name__)


class McpTransport:
    """Async context manager wrapping a standard MCP SDK ``ClientSession``.

    Usage::

        transport = McpTransport(config)
        async with transport:
            tools = await transport.list_tools()
            result = await transport.call_tool("foo", {"x": 1})
    """

    def __init__(self, config: McpServerConfig) -> None:
        self._config = config
        self._session: ClientSession | None = None
        self._exit_stack: AsyncExitStack | None = None

    # ------------------------------------------------------------------
    # Async context manager
    # ------------------------------------------------------------------

    async def __aenter__(self) -> McpTransport:
        self._exit_stack = AsyncExitStack()
        await self._exit_stack.__aenter__()

        try:
            read_stream, write_stream = await self._exit_stack.enter_async_context(
                self._open_transport(),
            )
            session = await self._exit_stack.enter_async_context(
                ClientSession(read_stream, write_stream),
            )
            await session.initialize()
            self._session = session
            return self
        except BaseException:
            await self._exit_stack.aclose()
            raise

    async def __aexit__(self, *args: Any) -> None:
        if self._exit_stack is not None:
            await self._exit_stack.aclose()
        self._session = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def list_tools(self) -> list[Tool]:
        """Return tool metadata from the connected MCP server."""
        self._require_session()
        assert self._session is not None  # for type checker
        result = await self._session.list_tools()
        return result.tools

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> CallToolResult:
        """Invoke *tool_name* and return the raw ``CallToolResult``."""
        self._require_session()
        assert self._session is not None  # for type checker
        return await self._session.call_tool(tool_name, arguments)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _require_session(self) -> None:
        if self._session is None:
            raise RuntimeError("McpTransport is not connected (call __aenter__ first)")

    def _open_transport(self) -> Any:
        """Return the appropriate transport async context manager."""
        cfg = self._config
        if cfg.transport == "stdio":
            from mcp.client.stdio import StdioServerParameters, stdio_client

            params = StdioServerParameters(
                command=cfg.command or "",
                args=cfg.args or [],
                env=cfg.env or None,
            )
            return stdio_client(params)

        if cfg.transport == "sse":
            from mcp.client.sse import sse_client

            return sse_client(
                url=cfg.url or "",
                headers=cfg.headers or None,
                timeout=cfg.timeout_seconds,
            )

        # Default: http / streamable_http
        from mcp.client.streamable_http import streamablehttp_client

        return streamablehttp_client(
            url=cfg.url or "",
            headers=cfg.headers or None,
            timeout=cfg.timeout_seconds,
        )


def build_transport(config: McpServerConfig) -> McpTransport:
    """Factory: build a :class:`McpTransport` from *config*.

    This replaces the previous ``_build_pydantic_ai_client`` function.
    """
    return McpTransport(config)
