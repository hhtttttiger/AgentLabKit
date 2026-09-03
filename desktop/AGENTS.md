# Desktop client

## 职责

`desktop` 是 standalone PySide6 client。它直接调用可复用的 package layer，不依赖 FastAPI backend、frontend、Redis 或 PostgreSQL。

## 边界

- `app/` 是 composition root：创建 components、连接 signals，并负责 shutdown。
- `core/` 负责 desktop configuration、package assembly，以及 Qt/asyncio bridge。
- `ui/` 发出 Qt signals，不得直接调用 LLM、storage 或 capture services。
- `tools/` 包含 desktop-specific tools；通过其 registry 注册新 tools，并将 filesystem access 保持在文档规定的 safety boundary 内。
- `capture/` 负责 screenshot selection 和 image analysis；与 UI composition 分离。
- `storage/` 负责 local SQLite persistence；不是 server memory/database layer。

不要让 desktop code 依赖 backend internals。对于 text-agent behavior，优先使用 `agent_runtime` 和 `llm_gateway` package protocols，并保留 local configuration/data paths。

## 关键路径

- `main.py` — desktop entrypoint。
- `app/desktop_app.py` — composition 和 lifecycle。
- `core/` — configuration 和 runtime assembly。
- `tools/`、`capture/`、`storage/`、`ui/`、`utils/` — local subsystems。

## 验证

有条件时运行相关 desktop tests。至少在安装 desktop dependencies 后 import 或执行变更模块；不要用 backend startup commands 验证 desktop-only changes。

## 参考

- [根目录 instructions](../AGENTS.md)
- [Agent Runtime](../packages/agent_runtime/AGENTS.md)
- [LLM Gateway](../packages/llm_gateway/AGENTS.md)
