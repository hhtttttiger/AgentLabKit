#!/usr/bin/env python3
"""使用真实 MCP Filesystem Server 进行端到端测试。

运行方式：
    python tests/test_real_mcp.py

前提条件：
    1. npx 已安装（已验证）
    2. pydantic-ai[mcp] 已安装（已验证）
    3. MCP server 会通过 npx -y 自动下载
"""

from __future__ import annotations

import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from agent_runtime.mcp.client import McpClientManager
from agent_runtime.mcp.adapter import McpToolAdapter
from agent_runtime.mcp.registry_bridge import McpRegistryBridge
from agent_runtime.mcp.contracts import McpServerConfig, McpConnectionState
from agent_runtime.tools.registry import DynamicToolRegistry
from agent_runtime.tools.executor import ToolExecutor
from agent_runtime.tools.contracts import ToolExecutionContext


# 颜色输出
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*70}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(70)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*70}{Colors.ENDC}\n")


def print_success(text: str):
    print(f"{Colors.OKGREEN}✅ {text}{Colors.ENDC}")


def print_error(text: str):
    print(f"{Colors.FAIL}❌ {text}{Colors.ENDC}")


def print_info(text: str):
    print(f"{Colors.OKCYAN}ℹ️  {text}{Colors.ENDC}")


def print_step(step: int, text: str):
    print(f"{Colors.OKCYAN}[{step}] {text}{Colors.ENDC}")


async def test_filesystem_mcp_server():
    """测试真实的 MCP Filesystem Server。"""

    print_header("真实 MCP Filesystem Server 测试")

    # 1. 配置 MCP server
    print_step(1, "配置 MCP Filesystem Server (stdio)")
    config = McpServerConfig(
        name="filesystem",
        transport="stdio",
        command="npx",
        args=[
            "-y",                      # 自动确认安装
            "@modelcontextprotocol/server-filesystem",
            "/tmp/mcp_test_dir"       # 允许访问的目录
        ],
        tool_name_prefix="fs_",
        timeout_seconds=30.0,
    )
    print(f"   命令: {config.command} {' '.join(config.args)}")
    print(f"   工具前缀: {config.tool_name_prefix}")

    # 2. 创建 Manager
    print_step(2, "创建 McpClientManager")
    manager = McpClientManager(configs=[config])
    print_info("初始状态: " + manager.get_connection_state("filesystem").value)

    # 3. 启动连接
    print_step(3, "启动 MCP Server 连接...")
    try:
        await manager.start()
        state = manager.get_connection_state("filesystem")

        if state == McpConnectionState.CONNECTED:
            print_success(f"连接成功! 状态: {state.value}")
        elif state == McpConnectionState.ERROR:
            print_error(f"连接失败，状态: {state.value}")
            print_info("可能原因：npx 无法下载 MCP server 或服务器启动失败")
            return False
        else:
            print_error(f"未知状态: {state.value}")
            return False

    except Exception as e:
        print_error(f"启动失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 4. 工具发现
    print_step(4, "发现可用工具...")
    try:
        tools = await manager.discover_tools("filesystem")
        print_success(f"发现 {len(tools)} 个工具:")
        for i, tool in enumerate(tools, 1):
            print(f"   {i}. {Colors.BOLD}{tool.name}{Colors.ENDC}")
            print(f"      描述: {tool.description}")
            if tool.input_schema:
                props = tool.input_schema.get("properties", {})
                required = tool.input_schema.get("required", [])
                if props:
                    print(f"      参数:")
                    for param_name, param_info in props.items():
                        req = " (必填)" if param_name in required else ""
                        param_type = param_info.get("type", "unknown")
                        print(f"        - {param_name}: {param_type}{req}")

    except Exception as e:
        print_error(f"工具发现失败: {e}")
        await manager.stop()
        return False

    # 5. 注册到 DynamicToolRegistry
    print_step(5, "注册工具到 DynamicToolRegistry...")
    adapter = McpToolAdapter(manager)
    registry = DynamicToolRegistry()
    bridge = McpRegistryBridge(manager, adapter, registry)

    try:
        count = await bridge.sync_server(config)
        print_success(f"已注册 {count} 个工具")

        all_specs = registry.list_all()
        print(f"\n   注册的工具列表:")
        for spec in all_specs:
            print(f"   - {Colors.BOLD}{spec.name}{Colors.ENDC}")
            print(f"     标签: {', '.join(sorted(spec.tags))}")
            print(f"     超时: {spec.timeout_seconds}s")

    except Exception as e:
        print_error(f"注册失败: {e}")
        await manager.stop()
        return False

    # 6. 执行工具
    print_step(6, "执行工具调用测试...")
    executor = ToolExecutor(registry)
    context = ToolExecutionContext(
        session_id="test-session-" + str(os.getpid()),
        trace_id="test-trace-" + str(os.getpid())
    )

    # 测试 1: 列出文件
    print(f"\n   {Colors.BOLD}测试 1: 读取文件内容{Colors.ENDC}")
    try:
        result = await executor.execute(
            registry,
            "fs_read_file",
            {"path": "/tmp/mcp_test_dir/test.txt"},
            context
        )
        if result.status == "success":
            print_success(f"读取成功!")
            print(f"   文件内容: {Colors.BOLD}{result.output}{Colors.ENDC}")
        else:
            print_error(f"执行失败: {result.error_message}")

    except Exception as e:
        print_error(f"工具调用异常: {e}")
        import traceback
        traceback.print_exc()

    # 测试 2: 写入文件
    print(f"\n   {Colors.BOLD}测试 2: 写入文件{Colors.ENDC}")
    try:
        result = await executor.execute(
            registry,
            "fs_write_file",
            {"path": "/tmp/mcp_test_dir/mcp_test_output.txt", "content": "Hello from MCP!"},
            context
        )
        if result.status == "success":
            print_success("写入成功!")
            print(f"   输出: {result.output}")
        else:
            print_error(f"执行失败: {result.error_message}")

    except Exception as e:
        print_error(f"工具调用异常: {e}")

    # 测试 3: 列出目录
    print(f"\n   {Colors.BOLD}测试 3: 列出目录{Colors.ENDC}")
    try:
        result = await executor.execute(
            registry,
            "fs_list_directory",
            {"path": "/tmp/mcp_test_dir"},
            context
        )
        if result.status == "success":
            print_success("列表成功!")
            print(f"   目录内容:\n{result.output}")
        else:
            print_error(f"执行失败: {result.error_message}")

    except Exception as e:
        print_error(f"工具调用异常: {e}")

    # 7. 清理
    print_step(7, "关闭连接...")
    await manager.stop()
    print_success("连接已关闭")

    return True


async def test_whitelist_filtering():
    """测试白名单过滤功能。"""
    print_header("白名单过滤测试")

    config = McpServerConfig(
        name="fs",
        transport="stdio",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", "/tmp/mcp_test_dir"],
    )

    manager = McpClientManager(configs=[config])

    try:
        await manager.start()
        if manager.get_connection_state("fs") != McpConnectionState.CONNECTED:
            print_error("连接失败")
            return False

        adapter = McpToolAdapter(manager)
        registry = DynamicToolRegistry()
        bridge = McpRegistryBridge(manager, adapter, registry)

        # 首先获取所有工具
        print_step(1, "获取所有可用工具...")
        await bridge.sync_server(config)
        all_tools = [s.name for s in registry.list_all()]
        print_info(f"总共 {len(all_tools)} 个工具: {', '.join(all_tools)}")

        # 清空并测试白名单
        print_step(2, "测试白名单 (只允许 read_file)...")
        bridge.deregister_server("fs")

        from agent_runtime.mcp.contracts import McpServerBinding
        binding = McpServerBinding(
            server_name="fs",
            tool_whitelist=["read_file"]
        )

        count = await bridge.sync_server(config, binding)
        filtered_tools = [s.name for s in registry.list_all()]

        print_success(f"白名单过滤后注册 {count} 个工具")
        print_info(f"过滤后工具: {', '.join(filtered_tools)}")

        # 验证: 只有 read_file 被注册，且数量为 1
        if "read_file" in filtered_tools and len(filtered_tools) == 1:
            print_success("白名单过滤正确!")
        else:
            print_error(f"白名单过滤失败: 期望只有 'read_file', 实际: {filtered_tools}")
            return False

    finally:
        await manager.stop()

    return True


async def main():
    """运行所有测试。"""
    print(f"\n{Colors.BOLD}{Colors.OKGREEN}╔════════════════════════════════════════════════════════════╗{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.OKGREEN}║     MCP Real Server End-to-End Test Suite              ║{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.OKGREEN}╚════════════════════════════════════════════════════════════╝{Colors.ENDC}")

    results = []

    # 测试 1: 基本 filesystem server
    success = await test_filesystem_mcp_server()
    results.append(("基本功能测试", success))

    if success:
        # 测试 2: 白名单过滤
        success = await test_whitelist_filtering()
        results.append(("白名单过滤测试", success))

    # 总结
    print_header("测试结果总结")
    passed = sum(1 for _, s in results if s)
    total = len(results)

    for name, success in results:
        status = f"{Colors.OKGREEN}PASS{Colors.ENDC}" if success else f"{Colors.FAIL}FAIL{Colors.ENDC}"
        print(f"   {status}  {name}")

    print(f"\n   总计: {passed}/{total} 通过")

    if passed == total:
        print(f"\n{Colors.OKGREEN}{Colors.BOLD}🎉 所有测试通过!{Colors.ENDC}\n")
        return 0
    else:
        print(f"\n{Colors.FAIL}{Colors.BOLD}⚠️  部分测试失败{Colors.ENDC}\n")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
