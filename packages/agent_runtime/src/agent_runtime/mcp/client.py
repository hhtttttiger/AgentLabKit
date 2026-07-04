"""McpClientManager — lifecycle management for MCP server connections.

Wraps the standard ``mcp`` SDK transports (stdio / SSE / streamable-HTTP) via
:class:`McpTransport` with a stable interface that is easy to mock in unit tests.
"""

from __future__ import annotations

import logging
from typing import Any, Protocol, runtime_checkable

from .contracts import McpConnectionState, McpServerConfig, McpToolInfo
from .transport import McpTransport, build_transport

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Testability seam: injectable MCP transport protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class McpServerClient(Protocol):
    """Minimal interface that MCP transports expose.

    The real implementation (:class:`McpTransport`) satisfies this protocol.
    Tests inject fakes instead.
    """

    async def __aenter__(self) -> "McpServerClient": ...
    async def __aexit__(self, *args: Any) -> None: ...

    async def list_tools(self) -> list[Any]:
        """Return tool metadata objects."""
        ...

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """Invoke a tool and return its result."""
        ...


# ---------------------------------------------------------------------------
# McpClientManager
# ---------------------------------------------------------------------------


class McpClientManager:
    """Manages the lifecycle of connections to one or more MCP servers.

    Dependency-injectable: pass *client_factory* in tests to avoid real
    MCP connections.

    Args:
        configs: List of server configurations to manage.
        client_factory: Callable ``(McpServerConfig) -> McpServerClient``.
            Defaults to :func:`build_transport`.
    """

    def __init__(
        self,
        configs: list[McpServerConfig],
        client_factory: Any = None,
    ) -> None:
        self._configs: dict[str, McpServerConfig] = {c.name: c for c in configs}
        self._factory = client_factory or build_transport
        self._clients: dict[str, McpServerClient] = {}
        self._states: dict[str, McpConnectionState] = {
            name: McpConnectionState.DISCONNECTED for name in self._configs
        }

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Connect to all configured MCP servers and enter their contexts."""
        for name, config in self._configs.items():
            self._states[name] = McpConnectionState.CONNECTING
            try:
                client = self._factory(config)
                await client.__aenter__()
                self._clients[name] = client
                self._states[name] = McpConnectionState.CONNECTED
                logger.info("mcp_connected server=%s", name)
            except Exception as exc:  # noqa: BLE001
                self._states[name] = McpConnectionState.ERROR
                logger.error("mcp_connect_failed server=%s error=%s", name, exc)

    async def stop(self) -> None:
        """Gracefully close all active MCP server connections."""
        for name, client in list(self._clients.items()):
            try:
                await client.__aexit__(None, None, None)
                logger.info("mcp_disconnected server=%s", name)
            except Exception as exc:  # noqa: BLE001
                logger.warning("mcp_disconnect_error server=%s error=%s", name, exc)
            finally:
                self._states[name] = McpConnectionState.DISCONNECTED
        self._clients.clear()

    # ------------------------------------------------------------------
    # Tool discovery
    # ------------------------------------------------------------------

    async def discover_tools(self, server_name: str) -> list[McpToolInfo]:
        """Return tool metadata from the named server.

        Raises:
            RuntimeError: If the server is not connected.
        """
        client = self._require_client(server_name)
        raw_tools = await client.list_tools()
        return [self._to_tool_info(t, server_name) for t in raw_tools]

    async def discover_all_tools(self) -> dict[str, list[McpToolInfo]]:
        """Discover tools from all connected servers."""
        result: dict[str, list[McpToolInfo]] = {}
        for name in self._clients:
            try:
                result[name] = await self.discover_tools(name)
            except Exception as exc:  # noqa: BLE001
                logger.error("mcp_discover_failed server=%s error=%s", name, exc)
                result[name] = []
        return result

    # ------------------------------------------------------------------
    # Tool invocation
    # ------------------------------------------------------------------

    async def call_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> str:
        """Invoke *tool_name* on *server_name* and return a text result.

        Raises:
            RuntimeError: If the server is not connected.
        """
        client = self._require_client(server_name)
        result = await client.call_tool(tool_name, arguments)
        return self._extract_text(result)

    # ------------------------------------------------------------------
    # State inspection
    # ------------------------------------------------------------------

    def get_connection_state(self, server_name: str) -> McpConnectionState:
        return self._states.get(server_name, McpConnectionState.DISCONNECTED)

    def connected_servers(self) -> list[str]:
        return list(self._clients.keys())

    def list_configs(self) -> list[McpServerConfig]:
        """Return the managed server configs in insertion order."""
        return list(self._configs.values())

    async def ensure_server(self, config: McpServerConfig) -> None:
        """Ensure *config* is connected, registering it if not yet managed.

        This is the Phase 2 entry point for definition-aware MCP: when a
        definition's ``mcp_bindings`` reference a server that was not present
        in the global ``AgentSettings.mcp_servers`` list, ``ensure_server``
        registers it at runtime and opens the connection.

        If the server is already connected, this is a no-op (connection reuse).
        If the server is in an error state, it will attempt to reconnect.

        Args:
            config: Server configuration to ensure is connected.
        """
        name = config.name

        # Already connected — reuse the existing connection.
        if name in self._clients:
            return

        # Register the config if this is the first time we see this server.
        if name not in self._configs:
            self._configs[name] = config
            self._states[name] = McpConnectionState.DISCONNECTED
            logger.debug("mcp_server_registered server=%s transport=%s", name, config.transport)

        # Attempt to connect (idempotent: if DISCONNECTED or ERROR, try again).
        state = self._states.get(name, McpConnectionState.DISCONNECTED)
        if state == McpConnectionState.CONNECTING:
            return  # connection already in flight

        self._states[name] = McpConnectionState.CONNECTING
        try:
            client = self._factory(config)
            await client.__aenter__()
            self._clients[name] = client
            self._states[name] = McpConnectionState.CONNECTED
            logger.info("mcp_connected server=%s (via ensure_server)", name)
        except Exception as exc:  # noqa: BLE001
            self._states[name] = McpConnectionState.ERROR
            logger.error("mcp_connect_failed server=%s error=%s", name, exc)
            raise


    def _require_client(self, server_name: str) -> McpServerClient:
        client = self._clients.get(server_name)
        if client is None:
            state = self._states.get(server_name, McpConnectionState.DISCONNECTED)
            raise RuntimeError(
                f"MCP server '{server_name}' is not connected (state={state.value})"
            )
        return client

    @staticmethod
    def _to_tool_info(raw: Any, server_name: str) -> McpToolInfo:
        """Convert an ``mcp.types.Tool`` (or fake) to :class:`McpToolInfo`."""
        # mcp.types.Tool exposes: name, description, inputSchema
        name = getattr(raw, "name", None) or str(raw)
        description = getattr(raw, "description", "") or ""
        schema: dict[str, Any] = {}
        for attr in ("inputSchema", "parameters_json_schema", "input_schema", "schema"):
            val = getattr(raw, attr, None)
            if isinstance(val, dict):
                schema = val
                break
        return McpToolInfo(
            name=name,
            description=description,
            input_schema=schema,
            server_name=server_name,
        )

    @staticmethod
    def _extract_text(result: Any) -> str:
        """Coerce an ``mcp.types.CallToolResult`` (or fake) to a plain string."""
        if isinstance(result, str):
            return result
        # mcp.types.CallToolResult has .content: list[TextContent | ...]
        content_list = getattr(result, "content", None)
        if isinstance(content_list, list):
            parts = []
            for item in content_list:
                text = getattr(item, "text", None)
                if text is not None:
                    parts.append(str(text))
            if parts:
                return "\n".join(parts)
        # fallback for simple objects
        text = getattr(result, "text", None) or getattr(result, "content", None)
        if text is not None:
            return str(text)
        return str(result)
