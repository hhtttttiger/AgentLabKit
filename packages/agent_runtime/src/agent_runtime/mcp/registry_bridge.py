"""McpRegistryBridge — batch-inject MCP tools into DynamicToolRegistry.

Orchestrates discovery (via McpClientManager), adaptation (via McpToolAdapter),
and registration in DynamicToolRegistry.  Supports per-server tool whitelisting
and clean deregistration by tag.

Phase 2 extension point: definition-aware bindings (per-agent tool whitelists
loaded from agent_mcp_bindings DB table) will be wired in here.  Search for
``# Phase 2`` comments to find the hook locations.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .adapter import McpToolAdapter
from .client import McpClientManager
from .contracts import McpServerBinding, McpServerConfig

if TYPE_CHECKING:
    from ..tools.registry import DynamicToolRegistry

logger = logging.getLogger(__name__)


class McpRegistryBridge:
    """Synchronises MCP server tools into a :class:`DynamicToolRegistry`.

    Args:
        client_manager: Manages MCP server connections and tool calls.
        adapter: Converts tool info to ToolSpec/ToolHandler pairs.
        registry: Target registry to populate.
    """

    def __init__(
        self,
        client_manager: McpClientManager,
        adapter: McpToolAdapter,
        registry: "DynamicToolRegistry",
    ) -> None:
        self._manager = client_manager
        self._adapter = adapter
        self._registry = registry

    # ------------------------------------------------------------------
    # Per-server sync
    # ------------------------------------------------------------------

    async def sync_server(
        self,
        config: McpServerConfig,
        binding: McpServerBinding | None = None,
    ) -> int:
        """Discover and register tools from *config*.

        Args:
            config: Server whose tools to sync.
            binding: Optional per-agent binding carrying a ``tool_whitelist``
                and ``is_enabled`` flag.

                # Phase 2: binding is populated from agent_mcp_bindings DB rows
                # loaded by the definition loader (agent-module Phase 4).

        Returns:
            Number of tools registered.
        """
        if binding is not None and not binding.is_enabled:
            logger.debug("mcp_sync_skipped server=%s reason=binding_disabled", config.name)
            return 0

        whitelist: frozenset[str] | None = None
        if binding is not None and binding.tool_whitelist is not None:
            whitelist = frozenset(binding.tool_whitelist)

        try:
            tools = await self._manager.discover_tools(config.name)
        except Exception as exc:  # noqa: BLE001
            logger.error("mcp_discover_failed server=%s error=%s", config.name, exc)
            return 0

        registered = 0
        for tool_info in tools:
            if whitelist is not None and tool_info.name not in whitelist:
                continue
            spec, handler = self._adapter.adapt(tool_info, config)
            # Replace any stale registration (e.g. server reconnect with new schema)
            self._registry.register_or_replace(spec, handler)
            registered += 1

        logger.info("mcp_sync_done server=%s tools_registered=%d", config.name, registered)
        return registered

    # ------------------------------------------------------------------
    # Bulk sync
    # ------------------------------------------------------------------

    async def sync_all(
        self,
        configs: list[McpServerConfig] | None = None,
        bindings: list[McpServerBinding] | None = None,
    ) -> dict[str, int]:
        """Sync tools from all connected servers.

        Args:
            configs: Servers to sync.  Defaults to all connected servers if
                ``None`` (requires the client_manager to expose the configs).
            bindings: Optional per-agent binding overrides keyed by server name.

                # Phase 2: populated from definition loader after agent-module
                # Phase 4 ships the agent_mcp_bindings loader.

        Returns:
            Mapping of ``{server_name: tool_count}``.
        """
        binding_map: dict[str, McpServerBinding] = {}
        if bindings:
            binding_map = {b.server_name: b for b in bindings}

        if configs is None:
            configs = self._manager.list_configs()
            if not configs:
                return {}

        results: dict[str, int] = {}
        for config in configs:
            binding = binding_map.get(config.name)
            results[config.name] = await self.sync_server(config, binding)
        return results

    # ------------------------------------------------------------------
    # Deregistration
    # ------------------------------------------------------------------

    def deregister_server(self, server_name: str) -> int:
        """Remove all tools registered from *server_name*.

        Tools are identified by the tag ``"mcp:<server_name>"``.

        Returns:
            Number of tools removed.
        """
        tag = f"mcp:{server_name}"
        to_remove = [
            spec.name
            for spec in self._registry.list_all()
            if tag in spec.tags
        ]
        for name in to_remove:
            self._registry.unregister(name)
        if to_remove:
            logger.info("mcp_deregister_done server=%s tools_removed=%d", server_name, len(to_remove))
        return len(to_remove)
