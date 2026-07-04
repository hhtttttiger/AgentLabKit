#!/usr/bin/env python3
"""手动功能验证脚本：演示 MCP 集成的端到端流程。

运行方式：
    python tests/manual_mcp_test.py

前提条件：
    - 安装依赖: pip install pydantic-ai[mcp]
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

from agent_runtime.mcp.client import McpClientManager
from agent_runtime.mcp.adapter import McpToolAdapter
from agent_runtime.mcp.registry_bridge import McpRegistryBridge
from agent_runtime.mcp.contracts import McpServerConfig
from agent_runtime.tools.registry import DynamicToolRegistry
from agent_runtime.tools.executor import ToolExecutor
from agent_runtime.tools.contracts import ToolExecutionContext


# ---------------------------------------------------------------------------
# Mock MCP Server (模拟文件系统工具)
# ---------------------------------------------------------------------------

def _make_mock_filesystem_server():
    """创建一个模拟的文件系统 MCP server。"""
    client = MagicMock()

    async def mock_enter():
        print("[Mock MCP Server] 连接已建立")
        return client

    async def mock_exit(*args):
        print("[Mock MCP Server] 连接已关闭")

    async def list_tools():
        # 返回模拟的工具列表
        tool1 = MagicMock()
        tool1.name = "read_file"
        tool1.description = "读取文件内容"
        tool1.parameters_json_schema = {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "文件路径"}
            },
            "required": ["path"]
        }

        tool2 = MagicMock()
        tool2.name = "write_file"
        tool2.description = "写入文件内容"
        tool2.parameters_json_schema = {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"}
            },
            "required": ["path", "content"]
        }

        return [tool1, tool2]

    async def call_tool(tool_name, arguments):
        print(f"[Mock MCP Server] 调用工具: {tool_name} 参数: {arguments}")
        if tool_name == "read_file":
            return f"文件内容: {arguments.get('path', '')} 的模拟数据"
        elif tool_name == "write_file":
            return f"已写入 {arguments.get('path', '')}"
        return "未知工具"

    client.__aenter__ = mock_enter
    client.__aexit__ = mock_exit
    client.list_tools = list_tools
    client.call_tool = call_tool
    return client


# ---------------------------------------------------------------------------
# 验证步骤
# ---------------------------------------------------------------------------

async def test_phase1_basic_workflow():
    """Phase 1 基本工作流验证。"""
    print("\n" + "="*60)
    print("验证 Phase 1: 基本工作流")
    print("="*60)

    # 1. 创建配置
    config = McpServerConfig(
        name="filesystem",
        transport="stdio",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem"],
        tool_name_prefix="fs_",
        tags=frozenset({"readonly"}),
    )
    print(f"\n1. MCP Server 配置: {config.name}")

    # 2. 创建 Manager 并启动
    mock_server = _make_mock_filesystem_server()
    manager = McpClientManager(
        configs=[config],
        client_factory=lambda c: mock_server
    )

    await manager.start()
    print(f"2. Manager 启动完成，连接状态: {manager.get_connection_state('filesystem')}")

    # 3. 工具发现
    tools = await manager.discover_tools("filesystem")
    print(f"3. 发现工具数量: {len(tools)}")
    for tool in tools:
        print(f"   - {tool.name}: {tool.description}")

    # 4. 适配并注册到 DynamicToolRegistry
    adapter = McpToolAdapter(manager)
    registry = DynamicToolRegistry()
    bridge = McpRegistryBridge(manager, adapter, registry)

    count = await bridge.sync_server(config)
    print(f"4. 已注册工具数量: {count}")

    # 5. 列出注册的工具
    all_specs = registry.list_all()
    print(f"5. Registry 中的工具:")
    for spec in all_specs:
        print(f"   - {spec.name}")
        print(f"     标签: {spec.tags}")
        print(f"     超时: {spec.timeout_seconds}s")

    # 6. 执行工具
    executor = ToolExecutor(registry)
    context = ToolExecutionContext(session_id="test-session", trace_id="test-trace")

    print("\n6. 执行工具测试:")
    result = await executor.execute("fs_read_file", {"path": "/tmp/test.txt"}, context)
    print(f"   结果状态: {result.status}")
    print(f"   结果输出: {result.output}")

    # 7. 清理
    await manager.stop()
    print("\n7. Manager 已停止")


async def test_phase2_whitelist():
    """Phase 2 白名单过滤验证。"""
    print("\n" + "="*60)
    print("验证 Phase 2: 白名单过滤")
    print("="*60)

    from agent_runtime.mcp.contracts import McpServerBinding

    config = McpServerConfig(
        name="db",
        transport="http",
        url="http://localhost:8080/mcp",
    )

    mock_server = _make_mock_filesystem_server()
    manager = McpClientManager(
        configs=[config],
        client_factory=lambda c: mock_server
    )
    await manager.start()

    adapter = McpToolAdapter(manager)
    registry = DynamicToolRegistry()
    bridge = McpRegistryBridge(manager, adapter, registry)

    # 测试 1: 无白名单（注册所有工具）
    print("\n1. 无白名单测试:")
    count1 = await bridge.sync_server(config, binding=None)
    print(f"   注册工具数: {count1}")
    print(f"   工具列表: {[s.name for s in registry.list_all()]}")

    # 清理
    bridge.deregister_server("db")

    # 测试 2: 有白名单（只注册指定工具）
    print("\n2. 白名单过滤测试 (只注册 read_file):")
    binding = McpServerBinding(
        server_name="db",
        tool_whitelist=["read_file"]
    )
    count2 = await bridge.sync_server(config, binding)
    print(f"   注册工具数: {count2}")
    print(f"   工具列表: {[s.name for s in registry.list_all()]}")

    # 测试 3: 禁用的绑定
    print("\n3. 禁用绑定测试:")
    bridge.deregister_server("db")
    disabled_binding = McpServerBinding(
        server_name="db",
        is_enabled=False
    )
    count3 = await bridge.sync_server(config, disabled_binding)
    print(f"   注册工具数: {count3} (应为 0)")

    await manager.stop()


async def test_connection_states():
    """连接状态转换验证。"""
    print("\n" + "="*60)
    print("验证: 连接状态转换")
    print("="*60)

    from agent_runtime.mcp.contracts import McpConnectionState

    config = McpServerConfig(
        name="test",
        transport="stdio",
        command="echo",
    )

    # 模拟连接失败
    def _failing_client(c):
        client = MagicMock()
        client.__aenter__ = AsyncMock(side_effect=ConnectionError("连接失败"))
        client.__aexit__ = AsyncMock(return_value=None)
        return client

    manager = McpClientManager(
        configs=[config],
        client_factory=_failing_client
    )

    print(f"\n1. 初始状态: {manager.get_connection_state('test')}")

    await manager.start()
    print(f"2. 启动后状态: {manager.get_connection_state('test')}")

    print("\n" + "="*60)


async def main():
    """运行所有验证测试。"""
    print("\n" + "🔧 MCP 模块功能验证".center(60, "="))

    try:
        await test_phase1_basic_workflow()
        await test_phase2_whitelist()
        await test_connection_states()

        print("\n" + "="*60)
        print("✅ 所有验证测试通过!")
        print("="*60 + "\n")

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
