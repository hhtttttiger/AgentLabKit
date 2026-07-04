"""Unit tests for MCP Phase 1 — contracts, client, adapter, registry bridge, settings."""

from __future__ import annotations

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from agent_runtime.mcp.contracts import (
    McpConnectionState,
    McpServerBinding,
    McpServerConfig,
    McpToolInfo,
)
from agent_runtime.mcp.client import McpClientManager
from agent_runtime.mcp.adapter import McpToolAdapter
from agent_runtime.mcp.registry_bridge import McpRegistryBridge
from agent_runtime.tools.contracts import ToolExecutionContext, ToolSpec
from agent_runtime.tools.registry import DynamicToolRegistry
from agent_runtime.config.agent import AgentSettings


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def make_stdio_config(**kwargs) -> McpServerConfig:
    defaults = dict(name="test-server", transport="stdio", command="npx")
    defaults.update(kwargs)
    return McpServerConfig(**defaults)


def make_http_config(**kwargs) -> McpServerConfig:
    defaults = dict(name="test-http", transport="http", url="http://localhost:3000/mcp")
    defaults.update(kwargs)
    return McpServerConfig(**defaults)


def make_tool_info(name="list_files", server_name="test-server") -> McpToolInfo:
    return McpToolInfo(
        name=name,
        description="List files in directory",
        input_schema={"type": "object", "properties": {"path": {"type": "string"}}},
        server_name=server_name,
    )


def make_fake_raw_tool(name: str, description: str = "A tool") -> MagicMock:
    """Fake ``mcp.types.Tool`` object."""
    raw = MagicMock()
    raw.name = name
    raw.description = description
    raw.inputSchema = {"type": "object", "properties": {}}
    return raw


def make_fake_client(tools: list | None = None, call_result: str = "ok") -> MagicMock:
    """Fake McpServerClient for injection."""
    client = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    client.list_tools = AsyncMock(return_value=tools or [make_fake_raw_tool("tool_a")])
    client.call_tool = AsyncMock(return_value=call_result)
    return client


def make_context() -> ToolExecutionContext:
    return ToolExecutionContext(session_id="s1", trace_id="t1")


# ---------------------------------------------------------------------------
# McpServerConfig validation
# ---------------------------------------------------------------------------


class TestMcpServerConfig:
    def test_stdio_valid(self):
        cfg = McpServerConfig(name="fs", transport="stdio", command="npx")
        assert cfg.command == "npx"
        assert cfg.transport == "stdio"

    def test_stdio_missing_command_raises(self):
        with pytest.raises(Exception):
            McpServerConfig(name="fs", transport="stdio")  # command absent

    def test_http_valid(self):
        cfg = McpServerConfig(name="api", transport="http", url="http://localhost/mcp")
        assert cfg.url == "http://localhost/mcp"

    def test_http_missing_url_raises(self):
        with pytest.raises(Exception):
            McpServerConfig(name="api", transport="http")

    def test_sse_missing_url_raises(self):
        with pytest.raises(Exception):
            McpServerConfig(name="api", transport="sse")

    def test_default_timeout(self):
        cfg = make_stdio_config()
        assert cfg.timeout_seconds == 30.0

    def test_tool_name_prefix(self):
        cfg = make_stdio_config(tool_name_prefix="fs_")
        assert cfg.tool_name_prefix == "fs_"

    def test_tags_default_empty(self):
        cfg = make_stdio_config()
        assert cfg.tags == frozenset()

    def test_custom_tags(self):
        cfg = make_stdio_config(tags=frozenset({"readonly"}))
        assert "readonly" in cfg.tags

    def test_frozen(self):
        cfg = make_stdio_config()
        with pytest.raises(Exception):
            cfg.name = "other"  # type: ignore[misc]

    def test_args_default_empty(self):
        cfg = make_stdio_config()
        assert cfg.args == []

    def test_args_populated(self):
        cfg = make_stdio_config(args=["-y", "@modelcontextprotocol/server-filesystem"])
        assert "-y" in cfg.args


# ---------------------------------------------------------------------------
# McpClientManager
# ---------------------------------------------------------------------------


class TestMcpClientManager:
    def _manager(self, configs=None, client=None):
        configs = configs or [make_stdio_config()]
        fake = client or make_fake_client()
        factory = MagicMock(return_value=fake)
        return McpClientManager(configs, client_factory=factory), fake

    @pytest.mark.asyncio
    async def test_start_connects(self):
        mgr, fake = self._manager()
        await mgr.start()
        fake.__aenter__.assert_called_once()
        assert mgr.get_connection_state("test-server") == McpConnectionState.CONNECTED

    @pytest.mark.asyncio
    async def test_stop_disconnects(self):
        mgr, fake = self._manager()
        await mgr.start()
        await mgr.stop()
        fake.__aexit__.assert_called_once()
        assert mgr.get_connection_state("test-server") == McpConnectionState.DISCONNECTED

    @pytest.mark.asyncio
    async def test_start_failure_sets_error_state(self):
        fake = AsyncMock()
        fake.__aenter__ = AsyncMock(side_effect=RuntimeError("conn refused"))
        factory = MagicMock(return_value=fake)
        mgr = McpClientManager([make_stdio_config()], client_factory=factory)
        await mgr.start()
        assert mgr.get_connection_state("test-server") == McpConnectionState.ERROR

    @pytest.mark.asyncio
    async def test_discover_tools_returns_tool_infos(self):
        raw = make_fake_raw_tool("list_files", "List files")
        mgr, _ = self._manager(client=make_fake_client(tools=[raw]))
        await mgr.start()
        tools = await mgr.discover_tools("test-server")
        assert len(tools) == 1
        assert tools[0].name == "list_files"
        assert tools[0].server_name == "test-server"

    @pytest.mark.asyncio
    async def test_discover_tools_not_connected_raises(self):
        mgr, _ = self._manager()
        # do NOT call start
        with pytest.raises(RuntimeError, match="not connected"):
            await mgr.discover_tools("test-server")

    @pytest.mark.asyncio
    async def test_call_tool_returns_string(self):
        fake = make_fake_client(call_result="file list here")
        mgr, _ = self._manager(client=fake)
        await mgr.start()
        result = await mgr.call_tool("test-server", "list_files", {"path": "/"})
        assert result == "file list here"
        fake.call_tool.assert_called_once_with("list_files", {"path": "/"})

    @pytest.mark.asyncio
    async def test_call_tool_not_connected_raises(self):
        mgr, _ = self._manager()
        with pytest.raises(RuntimeError):
            await mgr.call_tool("test-server", "tool", {})

    @pytest.mark.asyncio
    async def test_discover_all_tools(self):
        raw_a = make_fake_raw_tool("tool_a")
        raw_b = make_fake_raw_tool("tool_b")
        fake = make_fake_client(tools=[raw_a, raw_b])
        mgr, _ = self._manager(client=fake)
        await mgr.start()
        all_tools = await mgr.discover_all_tools()
        assert "test-server" in all_tools
        assert len(all_tools["test-server"]) == 2

    @pytest.mark.asyncio
    async def test_connected_servers_list(self):
        mgr, _ = self._manager()
        assert mgr.connected_servers() == []
        await mgr.start()
        assert "test-server" in mgr.connected_servers()

    @pytest.mark.asyncio
    async def test_stop_without_start_is_safe(self):
        mgr, _ = self._manager()
        await mgr.stop()  # should not raise

    def test_initial_state_disconnected(self):
        mgr, _ = self._manager()
        assert mgr.get_connection_state("test-server") == McpConnectionState.DISCONNECTED

    def test_unknown_server_state_disconnected(self):
        mgr, _ = self._manager()
        assert mgr.get_connection_state("nonexistent") == McpConnectionState.DISCONNECTED

    def test_list_configs_returns_managed_configs(self):
        config = make_stdio_config(name="fs")
        mgr, _ = self._manager(configs=[config])
        assert mgr.list_configs() == [config]


# ---------------------------------------------------------------------------
# McpToolAdapter
# ---------------------------------------------------------------------------


class TestMcpToolAdapter:
    def _adapter(self, configs=None):
        cfg = configs or [make_stdio_config()]
        fake = make_fake_client()
        factory = MagicMock(return_value=fake)
        mgr = McpClientManager(cfg, client_factory=factory)
        return McpToolAdapter(mgr), mgr

    def test_adapt_returns_spec_and_handler(self):
        adapter, _ = self._adapter()
        tool_info = make_tool_info()
        config = make_stdio_config()
        spec, handler = adapter.adapt(tool_info, config)
        assert isinstance(spec, ToolSpec)
        assert spec.name == "list_files"

    def test_name_prefix_applied(self):
        adapter, _ = self._adapter()
        tool_info = make_tool_info("list_files")
        config = make_stdio_config(tool_name_prefix="fs_")
        spec, _ = adapter.adapt(tool_info, config)
        assert spec.name == "fs_list_files"

    def test_no_prefix_when_none(self):
        adapter, _ = self._adapter()
        tool_info = make_tool_info("list_files")
        config = make_stdio_config(tool_name_prefix=None)
        spec, _ = adapter.adapt(tool_info, config)
        assert spec.name == "list_files"

    def test_mcp_tags_added(self):
        adapter, _ = self._adapter()
        tool_info = make_tool_info()
        config = make_stdio_config(name="my-server")
        spec, _ = adapter.adapt(tool_info, config)
        assert "mcp" in spec.tags
        assert "mcp:my-server" in spec.tags

    def test_server_tags_merged(self):
        adapter, _ = self._adapter()
        tool_info = make_tool_info()
        config = make_stdio_config(tags=frozenset({"readonly"}))
        spec, _ = adapter.adapt(tool_info, config)
        assert "readonly" in spec.tags
        assert "mcp" in spec.tags

    def test_timeout_inherited_from_config(self):
        adapter, _ = self._adapter()
        tool_info = make_tool_info()
        config = make_stdio_config(timeout_seconds=60.0)
        spec, _ = adapter.adapt(tool_info, config)
        assert spec.timeout_seconds == 60.0

    def test_schema_passthrough(self):
        adapter, _ = self._adapter()
        schema = {"type": "object", "properties": {"x": {"type": "integer"}}}
        tool_info = McpToolInfo(name="t", description="d", input_schema=schema, server_name="s")
        config = make_stdio_config()
        spec, _ = adapter.adapt(tool_info, config)
        assert spec.parameters_schema == schema

    def test_description_passthrough(self):
        adapter, _ = self._adapter()
        tool_info = make_tool_info()
        config = make_stdio_config()
        spec, _ = adapter.adapt(tool_info, config)
        assert spec.description == "List files in directory"

    @pytest.mark.asyncio
    async def test_handler_execute_calls_manager(self):
        adapter, mgr = self._adapter()
        fake = make_fake_client(call_result="result data")
        factory = MagicMock(return_value=fake)
        mgr2 = McpClientManager([make_stdio_config()], client_factory=factory)
        await mgr2.start()
        adapter2 = McpToolAdapter(mgr2)
        tool_info = make_tool_info()
        config = make_stdio_config()
        _, handler = adapter2.adapt(tool_info, config)
        ctx = make_context()
        result = await handler.execute({"path": "/"}, ctx)
        assert result.status == "success"
        assert result.output == "result data"

    @pytest.mark.asyncio
    async def test_handler_execute_error_returns_error_result(self):
        adapter, mgr = self._adapter()
        fake = make_fake_client()
        fake.call_tool = AsyncMock(side_effect=RuntimeError("server error"))
        factory = MagicMock(return_value=fake)
        mgr2 = McpClientManager([make_stdio_config()], client_factory=factory)
        await mgr2.start()
        adapter2 = McpToolAdapter(mgr2)
        tool_info = make_tool_info()
        config = make_stdio_config()
        _, handler = adapter2.adapt(tool_info, config)
        ctx = make_context()
        result = await handler.execute({}, ctx)
        assert result.status == "error"
        assert "server error" in (result.error_message or "")


# ---------------------------------------------------------------------------
# McpRegistryBridge
# ---------------------------------------------------------------------------


class TestMcpRegistryBridge:
    def _setup(self, tools=None, server_name="test-server"):
        config = make_stdio_config(name=server_name)
        raw_tools = tools or [make_fake_raw_tool("tool_a"), make_fake_raw_tool("tool_b")]
        fake = make_fake_client(tools=raw_tools)
        factory = MagicMock(return_value=fake)
        mgr = McpClientManager([config], client_factory=factory)
        adapter = McpToolAdapter(mgr)
        registry = DynamicToolRegistry()
        bridge = McpRegistryBridge(mgr, adapter, registry)
        return bridge, mgr, registry, config

    @pytest.mark.asyncio
    async def test_sync_server_registers_tools(self):
        bridge, mgr, registry, config = self._setup()
        await mgr.start()
        count = await bridge.sync_server(config)
        assert count == 2
        names = [s.name for s in registry.list_all()]
        assert "tool_a" in names
        assert "tool_b" in names

    @pytest.mark.asyncio
    async def test_sync_server_with_whitelist(self):
        bridge, mgr, registry, config = self._setup()
        await mgr.start()
        binding = McpServerBinding(server_name="test-server", tool_whitelist=["tool_a"])
        count = await bridge.sync_server(config, binding)
        assert count == 1
        names = [s.name for s in registry.list_all()]
        assert "tool_a" in names
        assert "tool_b" not in names

    @pytest.mark.asyncio
    async def test_sync_server_binding_disabled(self):
        bridge, mgr, registry, config = self._setup()
        await mgr.start()
        binding = McpServerBinding(server_name="test-server", is_enabled=False)
        count = await bridge.sync_server(config, binding)
        assert count == 0
        assert registry.list_all() == []

    @pytest.mark.asyncio
    async def test_sync_server_no_binding_registers_all(self):
        bridge, mgr, registry, config = self._setup()
        await mgr.start()
        count = await bridge.sync_server(config, binding=None)
        assert count == 2

    @pytest.mark.asyncio
    async def test_sync_server_replaces_existing_on_reconnect(self):
        bridge, mgr, registry, config = self._setup()
        await mgr.start()
        await bridge.sync_server(config)
        # sync again (simulates reconnect)
        count = await bridge.sync_server(config)
        assert count == 2
        # should still only have 2 tools (replaced, not duplicated)
        assert len(registry.list_all()) == 2

    @pytest.mark.asyncio
    async def test_sync_all_with_configs(self):
        bridge, mgr, registry, config = self._setup()
        await mgr.start()
        results = await bridge.sync_all(configs=[config])
        assert results["test-server"] == 2

    @pytest.mark.asyncio
    async def test_sync_all_without_configs_uses_manager_configs(self):
        bridge, mgr, registry, config = self._setup()
        await mgr.start()
        results = await bridge.sync_all(configs=None)
        assert results == {"test-server": 2}
        assert len(registry.list_all()) == 2

    def test_deregister_server_removes_tagged_tools(self):
        bridge, mgr, registry, config = self._setup()
        # Manually pre-populate registry with MCP-tagged tools
        spec_a = ToolSpec(
            name="tool_a",
            description="A",
            parameters_schema={},
            tags=frozenset({"mcp", "mcp:test-server"}),
        )
        spec_b = ToolSpec(
            name="tool_b",
            description="B",
            parameters_schema={},
            tags=frozenset({"mcp", "mcp:other-server"}),
        )
        from unittest.mock import AsyncMock as AM
        handler = MagicMock()
        registry.register(spec_a, handler)
        registry.register(spec_b, handler)
        removed = bridge.deregister_server("test-server")
        assert removed == 1
        remaining = [s.name for s in registry.list_all()]
        assert "tool_a" not in remaining
        assert "tool_b" in remaining

    def test_deregister_server_not_present_returns_zero(self):
        bridge, _, registry, _ = self._setup()
        count = bridge.deregister_server("nonexistent")
        assert count == 0

    @pytest.mark.asyncio
    async def test_sync_server_tags_tools_with_server_name(self):
        bridge, mgr, registry, config = self._setup(server_name="my-server")
        await mgr.start()
        await bridge.sync_server(config)
        for spec in registry.list_all():
            assert "mcp:my-server" in spec.tags
            assert "mcp" in spec.tags


# ---------------------------------------------------------------------------
# AgentSettings MCP fields
# ---------------------------------------------------------------------------


class TestAgentSettingsMcp:
    def test_enable_mcp_default_false(self):
        settings = AgentSettings()
        assert settings.enable_mcp is False

    def test_mcp_servers_default_empty(self):
        settings = AgentSettings()
        assert settings.mcp_servers == []

    def test_enable_mcp_true(self):
        settings = AgentSettings(enable_mcp=True)
        assert settings.enable_mcp is True

    def test_mcp_servers_populated(self):
        settings = AgentSettings(
            mcp_servers=[
                {
                    "name": "fs",
                    "transport": "stdio",
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-filesystem"],
                }
            ]
        )
        assert len(settings.mcp_servers) == 1
        assert settings.mcp_servers[0].name == "fs"

    def test_mcp_servers_parse_into_typed_configs(self):
        settings = AgentSettings(
            mcp_servers=[{"name": "fs", "transport": "stdio", "command": "npx"}]
        )
        config = settings.mcp_servers[0]
        assert isinstance(config, McpServerConfig)
        assert config.name == "fs"
        assert config.transport == "stdio"
