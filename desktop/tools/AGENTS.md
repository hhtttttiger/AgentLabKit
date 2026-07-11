# tools — 桌面端 Agent 工具

> **定位**：桌面端专用的 Agent 工具定义。参照 pi 的设计——工具与运行时分离，应用层组装注入。

## 设计原则

- 每个工具 = `ToolSpec`（元数据 + JSON Schema）+ `ToolHandler`（执行逻辑）
- 工具通过 `ToolRegistry.register()` 注册，`create_desktop_tool_registry()` 组装
- 工具不依赖 agent_runtime 内部实现，只依赖 `ToolSpec` / `ToolHandler` / `ToolResult` 协议
- 所有文件操作限制在用户 home 目录内（安全边界）

## 文件

| 文件 | 工具 | 说明 |
|------|------|------|
| `clipboard.py` | `clipboard_read` / `clipboard_write` | 读写系统剪贴板 |
| `screen.py` | `screenshot` | 全屏截图，返回 base64 PNG |
| `filesystem.py` | `read_file` / `list_dir` / `search_files` | 文件系统操作（home 目录内） |
| `bash.py` | `bash` | Shell 命令执行（默认不启用） |
| `registry.py` | — | `create_desktop_tool_registry()` 组装函数 |

## 工具清单

| 名称 | 类型 | 默认启用 | 说明 |
|------|------|---------|------|
| `clipboard_read` | read_only | ✅ | 读取剪贴板 |
| `clipboard_write` | write | ✅ | 写入剪贴板 |
| `screenshot` | read_only | ✅ | 全屏截图 |
| `read_file` | read_only | ✅ | 读文件内容 |
| `list_dir` | read_only | ✅ | 列目录 |
| `search_files` | read_only | ✅ | 搜索文件内容（grep） |
| `bash` | write | ❌ | Shell 命令（需显式启用） |

## 注册方式

```python
from tools.registry import create_desktop_tool_registry

# 默认不含 bash
registry = create_desktop_tool_registry()

# 启用 bash
registry = create_desktop_tool_registry(enable_bash=True)
```

## 新增工具

1. 在对应文件（或新建文件）中定义 `ToolSpec` + handler 类
2. handler 实现 `async def execute(self, arguments, context, on_update=None) -> ToolResult`
3. 在 `registry.py` 的 `create_desktop_tool_registry()` 中注册

## 另见

- [agent_runtime/AGENTS.md](../../packages/agent_runtime/AGENTS.md) — Agent 运行时（ToolSpec/ToolHandler 协议定义）
- [desktop/AGENTS.md](../AGENTS.md) — 桌面端总览
