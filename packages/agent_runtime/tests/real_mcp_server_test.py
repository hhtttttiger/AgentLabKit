#!/usr/bin/env python3
"""使用真实 MCP Server 进行端到端测试。

运行方式：
    python tests/real_mcp_server_test.py

前提条件：
    1. 安装 MCP server: npm install -g @modelcontextprotocol/server-filesystem
    2. 安装 Python 依赖: pip install pydantic-ai[mcp]

或者使用 docker 运行一个 HTTP MCP server：
    docker run -p 3000:3000 -v /tmp:/data mcp-server/filesystem
"""

from __future__ import annotations

import asyncio
from agent_runtime.mcp.client import McpClientManager
from agent_runtime.mcp.adapter import McpToolAdapter
from agent_runtime.mcp.registry_bridge import McpRegistryBridge
from agent_runtime.mcp.contracts import McpServerConfig
from agent_runtime.tools.registry import DynamicToolRegistry
from agent_runtime.tools.executor import ToolExecutor
from agent_runtime.tools.contracts import ToolExecutionContext


async def test_with_stdio_server():
    """测试 stdio 传输的 MCP server (需要安装 npx)。"""
    print("\n" + "="*60)
    print("测试: stdio MCP Server (@modelcontextprotocol/server-filesystem)")
    print("="*60)

    config = McpServerConfig(
        name="filesystem",
        transport="stdio",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
        tool_name_prefix="fs_",
    )

    manager = McpClientManager(configs=[config])

    try:
        print("\n1. 启动 MCP client...")
        await manager.start()

        if manager.get_connection_state("filesystem") != "connected":
            print("   ❌ 连接失败 - 请确保已安装: npm install -g @modelcontextprotocol/server-filesystem")
            return

        print("   ✅ 连接成功")

        print("\n2. 发现工具...")
        tools = await manager.discover_tools("filesystem")
        print(f"   发现 {len(tools)} 个工具:")
        for tool in tools:
            print(f"   - {tool.name}: {tool.description}")

        print("\n3. 注册到 DynamicToolRegistry...")
        adapter = McpToolAdapter(manager)
        registry = DynamicToolRegistry()
        bridge = McpRegistryBridge(manager, adapter, registry)

        count = await bridge.sync_server(config)
        print(f"   ✅ 已注册 {count} 个工具")

        print("\n4. 测试工具执行...")
        executor = ToolExecutor(registry)
        context = ToolExecutionContext(session_id="test", trace_id="trace")

        # 尝试调用一个工具（如 read_file）
        for spec in registry.list_all():
            if "read" in spec.name.lower() or "list" in spec.name.lower():
                print(f"   调用工具: {spec.name}")
                result = await executor.execute(spec.name, {"path": "/tmp"}, context)
                print(f"   状态: {result.status}")
                if result.status == "success":
                    print(f"   输出预览: {result.output[:200]}...")
                break

    finally:
        await manager.stop()
        print("\n5. 连接已关闭")


async def test_with_http_server():
    """测试 HTTP 传输的 MCP server。

    注意：这需要一个运行中的 HTTP MCP server。
    可以使用任何兼容 MCP 协议的 HTTP server。
    """
    print("\n" + "="*60)
    print("测试: HTTP MCP Server")
    print("="*60)

    config = McpServerConfig(
        name="http-mcp",
        transport="http",
        url="http://localhost:3000/mcp",
        headers={"Authorization": "Bearer test-token"},
        tool_name_prefix="http_",
    )

    manager = McpClientManager(configs=[config])

    try:
        print("\n1. 尝试连接 HTTP MCP server...")
        await manager.start()

        if manager.get_connection_state("http-mcp") != "connected":
            print("   ⚠️  连接失败 - 请确保 HTTP MCP server 正在运行")
            print("   可以使用: docker run -p 3000:3000 mcp-server/filesystem")
            return

        print("   ✅ 连接成功")

        print("\n2. 发现工具...")
        tools = await manager.discover_tools("http-mcp")
        print(f"   发现 {len(tools)} 个工具")

    finally:
        await manager.stop()


async def main():
    """运行真实 MCP server 测试。"""
    print("\n" + "🔧 MCP 真实 Server 端到端测试".center(60, "="))

    print("\n提示：如果测试失败，请确保：")
    print("  1. stdio 测试: npm install -g @modelcontextprotocol/server-filesystem")
    print("  2. HTTP 测试: 需要一个运行中的 HTTP MCP server")

    await test_with_stdio_server()
    # await test_with_http_server()  # 取消注释以测试 HTTP server

    print("\n" + "="*60)


if __name__ == "__main__":
    asyncio.run(main())
