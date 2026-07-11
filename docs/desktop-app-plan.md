# Desktop App Plan

> 状态：**Phase 0-3 完成**，Phase 4 待开始
> 创建日期：2026-07-11
> 最后更新：2026-07-11

## 当前进度

| Phase | 状态 | 产物 |
|-------|------|------|
| 0 环境验证 | ✅ | WSLg + PySide6 + Wayland |
| 1 骨架搭建 | ✅ | `pet.py` `tray.py` `chat.py` `main.py` |
| 2 接通 LLM | ✅ | `bootstrap.py` `async_bridge.py` `config.py` |
| 3 本地存储 | ✅ | `chat_store.py` `sqlite_memory_store.py` |
| 4 提供商切换 | 待做 | 设置面板 |
| 5 打磨 | 待做 | 动画、快捷键、打包 |

## 1. 目标

为 AgentLabKit 构建一个跨平台桌面客户端，提供：

- **桌宠**（Desktop Pet）：无边框、透明背景、置顶、可拖动的浮动角色
- **系统托盘**（System Tray）：图标 + 右键菜单，常驻后台
- **对话面板**（Chat Panel）：气泡消息 + 输入框的聊天 UI

## 2. 架构决策：桌面端即完整应用

桌面端是一个**独立的完整应用**，始终本地运行 `packages/` 层，不依赖 FastAPI 后端。
FastAPI 后端是另一个并列的部署形态（Web 服务），两者共享 `packages/` 但互不依赖。

唯一可配置的是 **LLM 提供商**，通过 `llm_gateway` 的 provider 适配器切换：

```
desktop_app/
│
├── GUI 层（PySide6）
│   ├── 桌宠窗口
│   ├── 托盘管理
│   └── 对话面板
│
└── 本地运行 packages（始终）
    ├── llm_gateway → 通过配置切换 provider
    │   ├── Ollama（本地，离线可用）
    │   ├── OpenAI（远程）
    │   ├── Anthropic（远程）
    │   └── 自建服务 / 其他兼容 API（远程）
    ├── agent_runtime → 本地执行 Agent
    ├── memory → SQLite 本地存储
    └── queue / cache → InMemory
```

## 3. 技术栈

| 组件 | 选择 | 理由 |
|------|------|------|
| GUI 框架 | **PySide6** | 唯一同时支持桌宠（透明置顶窗口）、托盘、对话面板的 Python 框架 |
| PySide6 协议 | **LGPL 3.0** | 与项目 MIT 协议兼容，无法律冲突 |
| 显示协议 | **Wayland** | 现代 Linux 显示协议，WSLg 原生支持 |
| 本地 LLM | **Ollama** | 本地模型推理，隐私优先，离线可用 |
| 本地存储 | **SQLite** | 轻量本地数据库，替代 PostgreSQL |

## 4. 复用现有 packages

| 包 | 桌面端用途 |
|---|-----------|
| `llm_gateway` | 直接调用，通过配置连接 Ollama 或远程提供商 |
| `agent_runtime` | 本地执行 Agent，工具调用，技能 |
| `memory` | `SqliteMemoryStore`（需新写，实现已有的 `MemoryStore` 协议） |
| `infra/cache` | `InMemoryCache`（已有） |
| `infra/queue` | `InMemoryQueue`（已有） |
| `db` | SQLite + JSONB 兼容层（测试中已有 JSONB→JSON 的方言 shim） |

## 5. 待新增实现

以下组件需要新建，但均有 Protocol/接口定义：

| 组件 | 接口 | 说明 |
|------|------|------|
| `SqliteMemoryStore` | `MemoryStore` | SQLite 实现的本地记忆存储 |
| `SqliteTraceStore` | `TraceStore` | SQLite 实现的本地追踪存储 |
| 桌面端组装层 | — | 替代 `backend/runtime/web_modules.py`，用 SQLite + InMemory 组装 packages |

## 6. 开发环境

- WSL2 + WSLg（Wayland）✅
- PySide6 6.11.1 ✅
- 中文字体：`fonts-wqy-zenhei` ✅
- 已知问题：WSLg 下托盘图标不可用（StatusNotifierWatcher 缺失）

## 7. 阶段规划

### Phase 0：环境验证 ✅
- [x] WSL2 GUI 通路验证（Wayland）
- [x] PySide6 Hello World 窗口
- [x] 中文字体安装（fonts-wqy-zenhei）

### Phase 1：骨架搭建 ✅
- [x] 桌宠窗口（透明、置顶、可拖动）→ `desktop/pet.py`
- [x] 系统托盘（图标 + 菜单）→ `desktop/tray.py`
- [x] 对话面板（基础聊天 UI）→ `desktop/chat.py`
- [x] 主入口整合 → `desktop/main.py`

### 遗留问题
- [ ] 桌宠初始位置不在右下角（Wayland 下屏幕几何获取问题，待调）
- [ ] 桌宠无法拖动（WSL2 + Wayland 下 `startSystemMove()` 和全局坐标均不生效，需在原生桌面环境测试确认）

### Phase 2：接通 LLM ✅
- [x] 桌面端组装层 → `desktop/bootstrap.py`（create_gateway，支持 OpenAI/Anthropic 兼容 API）
- [x] 异步桥接 → `desktop/async_bridge.py`（Qt 事件循环 ↔ asyncio）
- [x] 对话面板接通 llm_gateway → `desktop/main.py`（非流式调用）
- [x] 系统消息显示 → `ChatPanel.add_system_message()`
- [x] 配置文件 → `~/.config/agentlabkit/desktop.toml`（避免硬编码 API Key）
- [x] 单实例锁 → `fcntl.flock()` 防止重复启动
- [x] 日志 → `~/.config/agentlabkit/desktop.log`
- [x] 修复：DeepSeek 返回 finish_reason 为字符串时 `.value` 报错 → `providers/openai/text.py:95`

### Phase 3：本地存储 ✅
- [x] 对话历史持久化 → `desktop/chat_store.py`（SQLite，重启后恢复）
- [x] `SqliteMemoryStore` → `desktop/sqlite_memory_store.py`（MemoryStore 协议，纯 Python 余弦相似度）
- [ ] `SqliteTraceStore`（待实现，优先级低）

### Phase 4：图片理解（截屏 + Vision API）✅
- [x] 截屏 + 区域选择覆盖层 → `desktop/capture.py`（全屏截图、鼠标框选、ESC 取消）
- [x] 视觉管线 → `desktop/vision.py`（直接调用 OpenAI/Anthropic Vision API，httpx）
- [x] 📎 附件按钮 → `desktop/chat.py`（截图识别 / 文件选择器）
- [x] 图片消息气泡 → `ImageBubble` 类
- [x] 主流程集成 → `desktop/main.py`（窗口隐藏/恢复、异步分析）

### Phase 5：提供商切换 ✅
- [x] 设置面板 → `desktop/settings.py`（提供商预设、表单配置、密码显隐切换）
- [x] 动态切换 provider，无需重启 → `main.py`（_reinit_gateway）
- [x] 托盘菜单连接 → `tray.py`（settings_requested 信号）
- [x] 提供商预设：OpenAI / Anthropic / DeepSeek / Ollama / 自定义

### Phase 6：打磨
- [x] 桌宠动画/交互 → `desktop/pet.py`（idle/thinking/happy/sleepy 四状态，右键菜单互动）
- [x] 全局快捷键唤起 → `desktop/hotkey.py`（Ctrl+Space，pynput，可选依赖）
- [x] 剪贴板监听 → `desktop/clipboard_watcher.py`（QTimer 轮询 QClipboard）
- [ ] 打包分发（PyInstaller / Nuitka）
