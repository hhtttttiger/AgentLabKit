"""MCP contracts: configuration, state, and tool info data structures."""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class McpServerConfig(BaseModel, frozen=True):
    """Connection configuration for a single MCP server.

    Use ``transport="stdio"`` for local process servers (requires ``command``),
    or ``transport="http"``/``"sse"`` for remote servers (requires ``url``).
    """

    name: str
    """Unique identifier for this server, e.g. ``"filesystem"``."""

    transport: Literal["stdio", "http", "sse"]
    """Wire transport to use when connecting."""

    # stdio fields
    command: str | None = None
    """Executable to launch for stdio transport, e.g. ``"npx"``."""

    args: list[str] = Field(default_factory=list)
    """Arguments passed to the stdio command."""

    env: dict[str, str] = Field(default_factory=dict)
    """Extra environment variables for the stdio subprocess."""

    # http/sse fields
    url: str | None = None
    """Endpoint URL for http/sse transport, e.g. ``"http://localhost:3000/mcp"``."""

    headers: dict[str, str] = Field(default_factory=dict)
    """HTTP headers to include (e.g. auth tokens)."""

    # common fields
    timeout_seconds: float = 30.0
    """Default timeout for tool calls from this server."""

    tool_name_prefix: str | None = None
    """Optional prefix prepended to every tool name, e.g. ``"fs_"``."""

    tags: frozenset[str] = frozenset()
    """Extra tags merged into every tool registered from this server."""

    @model_validator(mode="after")
    def _validate_transport_fields(self) -> "McpServerConfig":
        if self.transport == "stdio" and not self.command:
            raise ValueError("stdio transport requires 'command'")
        if self.transport in ("http", "sse") and not self.url:
            raise ValueError(f"{self.transport} transport requires 'url'")
        return self


class McpServerBinding(BaseModel, frozen=True):
    """Per-agent-definition binding referencing a :class:`McpServerConfig`.

    Stored in ``agent_mcp_bindings`` (managed by the .NET plane).
    Phase 2 will load these via the definition loader.
    """

    server_name: str
    """Must match a ``McpServerConfig.name`` known to the runtime."""

    is_enabled: bool = True

    tool_whitelist: list[str] | None = None
    """When set, only tools in this list are registered for the agent."""

    config_overrides: dict[str, Any] = Field(default_factory=dict)
    """Runtime config overrides (e.g. additional headers)."""


class McpConnectionState(str, Enum):
    """Observable lifecycle state of a managed MCP server connection."""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


class McpToolInfo(BaseModel):
    """Metadata for a single tool exposed by an MCP server."""

    name: str
    description: str
    input_schema: dict[str, Any]
    server_name: str
