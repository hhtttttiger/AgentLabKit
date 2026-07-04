"""Unit tests for MCP Phase 2 — definition-aware MCP bindings.

Covers:
- McpBindingSnapshot data model
- SqlAlchemyAgentDefinitionLoader._load_mcp_bindings (via full _load_from_db)
- McpClientManager.ensure_server (connection reuse, dynamic registration, error)
- AgentRuntime._ensure_mcp_for_definition (wiring, whitelist, disabled bindings)
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, call, patch

from agent_runtime.definition.models import AgentDefinitionSnapshot, McpBindingSnapshot
from agent_runtime.mcp.contracts import (
    McpConnectionState,
    McpServerBinding,
    McpServerConfig,
)
from agent_runtime.mcp.client import McpClientManager
from agent_runtime.mcp.adapter import McpToolAdapter
from agent_runtime.mcp.registry_bridge import McpRegistryBridge
from agent_runtime.tools.registry import DynamicToolRegistry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_tool_info(name: str, description: str = "desc") -> object:
    """Create a plain tool info object (avoids MagicMock.name special attribute)."""
    class _ToolInfo:
        pass
    t = _ToolInfo()
    t.name = name
    t.description = description
    t.input_schema = {"type": "object", "properties": {}}
    t.parameters_json_schema = {"type": "object", "properties": {}}
    t.server_name = "fs"
    return t


def _make_fake_client(tools: list | None = None) -> MagicMock:
    """Return a mock that satisfies the McpServerClient protocol."""
    client = MagicMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    raw_tools = tools or [
        _make_tool_info("tool_a", "desc_a"),
        _make_tool_info("tool_b", "desc_b"),
    ]
    client.list_tools = AsyncMock(return_value=raw_tools)
    client.call_tool = AsyncMock(return_value="result")
    return client


def _make_manager(server_name: str = "fs", command: str = "npx") -> tuple[McpClientManager, MagicMock]:
    config = McpServerConfig(name=server_name, transport="stdio", command=command)
    fake = _make_fake_client()
    manager = McpClientManager(configs=[config], client_factory=lambda c: fake)
    return manager, fake


# ---------------------------------------------------------------------------
# McpBindingSnapshot
# ---------------------------------------------------------------------------


class TestMcpBindingSnapshot:
    def test_defaults(self):
        snap = McpBindingSnapshot(server_name="fs")
        assert snap.is_enabled is True
        assert snap.tool_whitelist is None
        assert snap.server_config_json == {}

    def test_immutable(self):
        snap = McpBindingSnapshot(server_name="fs")
        with pytest.raises((AttributeError, TypeError)):
            snap.server_name = "other"  # type: ignore[misc]

    def test_whitelist_stored_as_tuple(self):
        snap = McpBindingSnapshot(server_name="db", tool_whitelist=("read", "write"))
        assert isinstance(snap.tool_whitelist, tuple)
        assert snap.tool_whitelist == ("read", "write")

    def test_config_json_stored(self):
        config_json = {"name": "fs", "transport": "stdio", "command": "npx"}
        snap = McpBindingSnapshot(server_name="fs", server_config_json=config_json)
        assert snap.server_config_json["transport"] == "stdio"

    def test_disabled_binding(self):
        snap = McpBindingSnapshot(server_name="fs", is_enabled=False)
        assert snap.is_enabled is False


# ---------------------------------------------------------------------------
# McpClientManager.ensure_server
# ---------------------------------------------------------------------------


class TestEnsureServer:
    @pytest.mark.asyncio
    async def test_already_connected_is_noop(self):
        manager, fake = _make_manager()
        await manager.start()
        assert manager.get_connection_state("fs") == McpConnectionState.CONNECTED

        config2 = McpServerConfig(name="fs", transport="stdio", command="npx")
        factory_spy = MagicMock(return_value=fake)
        manager._factory = factory_spy

        await manager.ensure_server(config2)

        # factory should NOT be called again — connection is reused
        factory_spy.assert_not_called()

    @pytest.mark.asyncio
    async def test_new_server_gets_connected(self):
        manager, _ = _make_manager()
        await manager.start()

        new_fake = _make_fake_client()
        new_config = McpServerConfig(name="new-server", transport="http", url="http://localhost:8080")
        manager._factory = lambda c: new_fake

        await manager.ensure_server(new_config)

        assert manager.get_connection_state("new-server") == McpConnectionState.CONNECTED
        assert "new-server" in manager.connected_servers()

    @pytest.mark.asyncio
    async def test_new_server_registered_in_configs(self):
        manager, _ = _make_manager()
        await manager.start()

        new_config = McpServerConfig(name="db", transport="http", url="http://db:9000")
        new_fake = _make_fake_client()
        manager._factory = lambda c: new_fake

        await manager.ensure_server(new_config)

        configs_map = {c.name: c for c in manager.list_configs()}
        assert "db" in configs_map
        assert configs_map["db"].url == "http://db:9000"

    @pytest.mark.asyncio
    async def test_ensure_server_connection_error_raises(self):
        manager, _ = _make_manager()
        bad_client = MagicMock()
        bad_client.__aenter__ = AsyncMock(side_effect=ConnectionRefusedError("refused"))
        bad_client.__aexit__ = AsyncMock(return_value=None)
        manager._factory = lambda c: bad_client

        new_config = McpServerConfig(name="bad", transport="http", url="http://bad:9999")
        with pytest.raises(ConnectionRefusedError):
            await manager.ensure_server(new_config)

        assert manager.get_connection_state("bad") == McpConnectionState.ERROR

    @pytest.mark.asyncio
    async def test_ensure_server_existing_config_disconnected_reconnects(self):
        """Server already registered but not yet started → ensure_server connects it."""
        config = McpServerConfig(name="lazy", transport="http", url="http://lazy:8080")
        fake = _make_fake_client()
        manager = McpClientManager(configs=[config], client_factory=lambda c: fake)
        # Do NOT call start() — server is registered but disconnected

        await manager.ensure_server(config)

        assert manager.get_connection_state("lazy") == McpConnectionState.CONNECTED

    @pytest.mark.asyncio
    async def test_connecting_state_is_noop(self):
        """If state is CONNECTING, ensure_server should not attempt another connect."""
        config = McpServerConfig(name="fs", transport="stdio", command="npx")
        factory_spy = MagicMock()
        manager = McpClientManager(configs=[config], client_factory=factory_spy)
        manager._states["fs"] = McpConnectionState.CONNECTING

        await manager.ensure_server(config)

        factory_spy.assert_not_called()


# ---------------------------------------------------------------------------
# AgentRuntime._ensure_mcp_for_definition
# ---------------------------------------------------------------------------


def _make_definition_with_bindings(
    *,
    server_name: str = "fs",
    whitelist: tuple[str, ...] | None = None,
    is_enabled: bool = True,
) -> AgentDefinitionSnapshot:
    snap = McpBindingSnapshot(
        server_name=server_name,
        is_enabled=is_enabled,
        tool_whitelist=whitelist,
        server_config_json={"name": server_name, "transport": "stdio", "command": "npx"},
    )
    return AgentDefinitionSnapshot(
        agent_key="test-agent",
        version_number=1,
        display_name="Test",
        mcp_bindings=(snap,),
    )


class TestEnsureMcpForDefinition:
    """Tests for AgentRuntime._ensure_mcp_for_definition via lightweight stubs."""

    def _make_stub(self, fake_client=None, mcp_enabled=True):
        """Create a minimal stub with the MCP attributes AgentRuntime needs."""
        from agent_runtime.mcp.client import McpClientManager
        from agent_runtime.mcp.adapter import McpToolAdapter
        from agent_runtime.mcp.registry_bridge import McpRegistryBridge
        from agent_runtime.runtime.engine import AgentRuntime

        registry = DynamicToolRegistry()
        real_fake = fake_client or _make_fake_client()
        manager = McpClientManager(configs=[], client_factory=lambda c: real_fake)
        adapter = McpToolAdapter(manager)
        bridge = McpRegistryBridge(manager, adapter, registry)

        class _Stub:
            _mcp_manager = manager if mcp_enabled else None
            _mcp_bridge = bridge if mcp_enabled else None
            ensure_mcp = AgentRuntime._ensure_mcp_for_definition

        stub = _Stub()
        return stub, manager, bridge, registry, real_fake

    @pytest.mark.asyncio
    async def test_no_mcp_manager_is_safe_noop(self):
        """When no mcp_manager is wired, method exits silently."""
        stub, manager, bridge, registry, fake = self._make_stub(mcp_enabled=False)
        definition = _make_definition_with_bindings()
        await stub.ensure_mcp(definition)  # must not raise

    @pytest.mark.asyncio
    async def test_no_definition_is_safe_noop(self):
        """Passing None definition exits silently."""
        stub, manager, bridge, registry, fake = self._make_stub()
        await stub.ensure_mcp(None)

    @pytest.mark.asyncio
    async def test_disabled_binding_is_skipped(self):
        """Bindings with is_enabled=False do not trigger ensure_server."""
        stub, manager, bridge, registry, fake = self._make_stub()
        ensure_spy = AsyncMock()
        manager.ensure_server = ensure_spy

        definition = _make_definition_with_bindings(is_enabled=False)
        await stub.ensure_mcp(definition)
        ensure_spy.assert_not_called()

    @pytest.mark.asyncio
    async def test_valid_binding_calls_ensure_server(self):
        """Enabled binding causes ensure_server to be called with reconstructed config."""
        stub, manager, bridge, registry, fake = self._make_stub()
        ensure_spy = AsyncMock()
        manager.ensure_server = ensure_spy
        sync_spy = AsyncMock(return_value={"fs": 2})
        bridge.sync_all = sync_spy

        definition = _make_definition_with_bindings(server_name="fs", whitelist=("read_file",))
        await stub.ensure_mcp(definition)

        ensure_spy.assert_awaited_once()
        called_config = ensure_spy.await_args[0][0]
        assert called_config.name == "fs"
        assert called_config.transport == "stdio"

    @pytest.mark.asyncio
    async def test_whitelist_passed_to_sync_all(self):
        """tool_whitelist in binding snapshot is forwarded to sync_all."""
        stub, manager, bridge, registry, fake = self._make_stub()
        manager.ensure_server = AsyncMock()
        sync_spy = AsyncMock(return_value={"fs": 1})
        bridge.sync_all = sync_spy

        definition = _make_definition_with_bindings(whitelist=("read_file", "list_dir"))
        await stub.ensure_mcp(definition)

        sync_spy.assert_awaited_once()
        call_kwargs = sync_spy.await_args.kwargs
        bindings_arg = call_kwargs.get("bindings", [])
        assert len(bindings_arg) == 1
        assert bindings_arg[0].tool_whitelist == ["read_file", "list_dir"]

    @pytest.mark.asyncio
    async def test_none_whitelist_passes_through(self):
        """When tool_whitelist is None (all tools), binding.tool_whitelist stays None."""
        stub, manager, bridge, registry, fake = self._make_stub()
        manager.ensure_server = AsyncMock()
        sync_spy = AsyncMock(return_value={"fs": 2})
        bridge.sync_all = sync_spy

        definition = _make_definition_with_bindings(whitelist=None)
        await stub.ensure_mcp(definition)

        call_kwargs = sync_spy.await_args.kwargs
        bindings_arg = call_kwargs.get("bindings", [])
        assert bindings_arg[0].tool_whitelist is None

    @pytest.mark.asyncio
    async def test_invalid_config_json_is_skipped_with_log(self):
        """Malformed server_config_json logs an error and skips that server."""
        stub, manager, bridge, registry, fake = self._make_stub()
        ensure_spy = AsyncMock()
        manager.ensure_server = ensure_spy
        sync_spy = AsyncMock(return_value={})
        bridge.sync_all = sync_spy

        # Bad config: missing required 'transport' field
        bad_snap = McpBindingSnapshot(
            server_name="broken",
            is_enabled=True,
            server_config_json={"name": "broken"},  # missing 'transport'
        )
        definition = AgentDefinitionSnapshot(
            agent_key="x", version_number=1, display_name="X",
            mcp_bindings=(bad_snap,),
        )
        # Should not raise — just skip
        await stub.ensure_mcp(definition)
        ensure_spy.assert_not_awaited()
        sync_spy.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_multiple_bindings_all_processed(self):
        """Multiple enabled bindings each call ensure_server once."""
        stub, manager, bridge, registry, fake = self._make_stub()
        ensure_spy = AsyncMock()
        manager.ensure_server = ensure_spy
        bridge.sync_all = AsyncMock(return_value={"fs": 1, "db": 1})

        snap_a = McpBindingSnapshot(
            server_name="fs", server_config_json={"name": "fs", "transport": "stdio", "command": "npx"}
        )
        snap_b = McpBindingSnapshot(
            server_name="db", server_config_json={"name": "db", "transport": "http", "url": "http://db"}
        )
        definition = AgentDefinitionSnapshot(
            agent_key="multi", version_number=1, display_name="Multi",
            mcp_bindings=(snap_a, snap_b),
        )
        await stub.ensure_mcp(definition)
        assert ensure_spy.await_count == 2
        server_names = {c[0][0].name for c in ensure_spy.await_args_list}
        assert server_names == {"fs", "db"}


# ---------------------------------------------------------------------------
# Integration: McpRegistryBridge.sync_all with whitelist filtering
# ---------------------------------------------------------------------------


class TestSyncAllWithBindingWhitelist:
    def _setup(self):
        raw_tools = [
            _make_tool_info("read_file", "r"),
            _make_tool_info("write_file", "w"),
            _make_tool_info("delete_file", "d"),
        ]

        fake = _make_fake_client(tools=raw_tools)
        config = McpServerConfig(name="fs", transport="stdio", command="npx")
        manager = McpClientManager(configs=[config], client_factory=lambda c: fake)
        registry = DynamicToolRegistry()
        adapter = McpToolAdapter(manager)
        bridge = McpRegistryBridge(manager, adapter, registry)
        return bridge, manager, registry, config

    @pytest.mark.asyncio
    async def test_whitelist_restricts_registered_tools(self):
        bridge, manager, registry, config = self._setup()
        await manager.start()

        binding = McpServerBinding(server_name="fs", tool_whitelist=["read_file", "write_file"])
        count = await bridge.sync_server(config, binding)

        assert count == 2
        names = {s.name for s in registry.list_all()}
        assert "read_file" in names
        assert "write_file" in names
        assert "delete_file" not in names

    @pytest.mark.asyncio
    async def test_no_whitelist_registers_all_tools(self):
        bridge, manager, registry, config = self._setup()
        await manager.start()

        binding = McpServerBinding(server_name="fs", tool_whitelist=None)
        count = await bridge.sync_server(config, binding)

        assert count == 3

    @pytest.mark.asyncio
    async def test_empty_whitelist_registers_nothing(self):
        bridge, manager, registry, config = self._setup()
        await manager.start()

        binding = McpServerBinding(server_name="fs", tool_whitelist=[])
        count = await bridge.sync_server(config, binding)

        assert count == 0
        assert len(registry.list_all()) == 0

    @pytest.mark.asyncio
    async def test_connection_reuse_across_two_syncs(self):
        """Second sync_all reuses the same client, not a new connection."""
        bridge, manager, registry, config = self._setup()
        await manager.start()

        # Spy on the factory to verify it's not called again
        call_count = [0]
        original_factory = manager._factory

        def spy_factory(c):
            call_count[0] += 1
            return original_factory(c)

        manager._factory = spy_factory

        await bridge.sync_all(configs=[config])
        await bridge.sync_all(configs=[config])

        # factory called 0 additional times after start() (already connected)
        assert call_count[0] == 0
