"""MCP (Model Context Protocol) integration package.

Uses the standard ``mcp`` Python SDK for transport (stdio / SSE / streamable-HTTP).
"""

from .contracts import McpConnectionState, McpServerBinding, McpServerConfig, McpToolInfo

__all__ = [
    "McpClientManager",
    "McpConnectionState",
    "McpRegistryBridge",
    "McpServerBinding",
    "McpServerConfig",
    "McpToolAdapter",
    "McpToolInfo",
    "McpTransport",
    "build_transport",
]


def __getattr__(name: str):
    if name == "McpClientManager":
        from .client import McpClientManager

        return McpClientManager
    if name == "McpRegistryBridge":
        from .registry_bridge import McpRegistryBridge

        return McpRegistryBridge
    if name == "McpToolAdapter":
        from .adapter import McpToolAdapter

        return McpToolAdapter
    if name == "McpTransport":
        from .transport import McpTransport

        return McpTransport
    if name == "build_transport":
        from .transport import build_transport

        return build_transport
    raise AttributeError(name)
