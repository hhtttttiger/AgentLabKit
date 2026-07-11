# desktop — 桌面客户端

> **定位**：AgentLabKit 的桌面端。PySide6 桌宠 + Agent 对话 + 工具调用 + 截图识别 + 本地记忆。独立于 Web 端，通过 agent_runtime 获得完整 Agent 能力。

## 系统中的角色

```
用户 ──▶ desktop (PySide6)  ← 本模块
            │
            ├─▶ agent_runtime (Agent 编排：多轮上下文、工具调用、流式响应)
            │     └─▶ llm_gateway (LLM 调用)
            ├─▶ Vision API (图片理解，httpx 直连)
            └─▶ SQLite (聊天历史 + 记忆存储)
```

**关键约束**：
- 桌面端**不依赖** backend / frontend / Redis / PostgreSQL
- 文本对话通过 `agent_runtime`（流式响应 + 工具调用 + 上下文管理）
- Vision 调用因 Gateway 暂不支持多模态而直连 API
- 工具定义在 `desktop/tools/`，参照 pi 的设计——与运行时分离，应用层组装注入
- 配置存储在 `~/.config/agentlabkit/desktop.toml`，数据存储在 `~/.config/agentlabkit/`

## 目录结构

```
desktop/
├── main.py              # 入口：单实例锁 + 启动
├── app/
│   └── desktop_app.py   # DesktopApp 主控制器（组装所有组件）
├── ui/
│   ├── pet.py           # 桌宠窗口（动画状态机 + 拖动 + 右键菜单）
│   ├── tray.py          # 系统托盘（图标 + 菜单）
│   ├── chat.py          # 对话面板（气泡 + 流式消息 + 输入 + 图片消息）
│   └── settings.py      # 设置面板（提供商预设 + 表单）
├── tools/               # Agent 工具定义（参照 pi 的工具分离模式）
│   ├── registry.py      # create_desktop_tool_registry() 组装函数
│   ├── clipboard.py     # clipboard_read / clipboard_write
│   ├── screen.py        # screenshot（全屏截图）
│   ├── filesystem.py    # read_file / list_dir / search_files
│   └── bash.py          # bash 命令执行（默认不启用）
├── capture/
│   ├── screen.py        # 截屏 + 区域选择覆盖层（交互式，供用户使用）
│   └── vision.py        # Vision API（OpenAI / Anthropic 直连）
├── core/
│   ├── config.py        # 配置管理（AppConfig / LLMConfig，TOML 序列化）
│   ├── bootstrap.py     # create_agent() 工厂（AgentModule 组装）
│   └── async_bridge.py  # Qt↔asyncio 桥接（run_async + run_async_stream）
├── storage/
│   ├── chat_store.py    # 聊天历史持久化（SQLite）
│   └── memory_store.py  # 记忆存储（MemoryStore 协议，SQLite + 余弦相似度）
└── utils/
    ├── hotkey.py        # 全局快捷键（pynput，可选依赖）
    └── clipboard.py     # 剪贴板监听（QClipboard 轮询）
```

## 依赖方向

```
main.py
  └─▶ app/desktop_app.py（主控制器）
        ├─▶ ui/*        （界面组件，仅依赖 PySide6）
        ├─▶ tools/*     （Agent 工具，依赖 agent_runtime 的 ToolSpec/ToolHandler）
        ├─▶ capture/*   （截屏 + Vision API）
        ├─▶ core/*      （配置 + Agent 组装 + 异步桥接）
        ├─▶ storage/*   （SQLite 存储）
        └─▶ utils/*     （快捷键 + 剪贴板）
```

**内部依赖规则**：
- `core/config.py` 是基础层，不依赖其他内部模块
- `core/bootstrap.py` 依赖 `agent_runtime` 和 `llm_gateway`
- `tools/*` 依赖 `agent_runtime` 的 `ToolSpec` / `ToolHandler` / `ToolResult` 协议
- `app/desktop_app.py` 依赖所有模块（组装层）
- 其余模块仅依赖 PySide6 / 标准库

## 消息流程

```
用户输入 → ChatPanel.message_sent
  → DesktopApp._on_message_sent
    → ChatStore.add("user", text)
    → ChatPanel.start_streaming_message()
    → AgentTurnRequest(session_id, user_message, history)
    → run_async_stream(runtime.stream_turn(request))
      → 流式事件: reply_delta → ChatPanel.append_streaming_text()
                  tool_call  → 显示工具调用
                  tool_result → 记录日志
                  reply_completed → ChatStore.add("assistant")
    → ChatPanel.finish_streaming()
```

## 技术栈

- **GUI**: PySide6 6.11.1（Qt 6 for Python）
- **Agent**: agent_runtime（多轮上下文、工具调用、流式响应）
- **LLM**: llm_gateway（通过 agent_runtime）+ httpx 直连（Vision）
- **存储**: SQLite（聊天 + 记忆）
- **异步**: QThread + asyncio 事件循环桥接（支持流式）
- **可选**: pynput（全局快捷键）

## 配置

`~/.config/agentlabkit/desktop.toml`：

```toml
[llm]
provider = "openai"          # openai | anthropic
base_url = "https://api.openai.com/v1"
api_key = "sk-..."
model = "gpt-4o-mini"
```

## 运行

```bash
cd desktop && python main.py
```

## 另见

- [根 AGENTS.md](../AGENTS.md) — 全局架构
- [packages/agent_runtime/AGENTS.md](../packages/agent_runtime/AGENTS.md) — Agent 运行时
- [packages/llm_gateway/AGENTS.md](../packages/llm_gateway/AGENTS.md) — LLM Gateway
- [tools/AGENTS.md](tools/AGENTS.md) — 桌面端工具定义
