<!-- Parent: ../../AGENTS.md -->
# Desktop core

`core` 是 desktop foundation，必须独立于其他 desktop subsystems。

- `config.py` 负责 `AppConfig`/`LLMConfig` 在 `~/.config/agentlabkit/desktop.toml` 的 persistence。
- `bootstrap.py` 组装可复用的 LLM/agent packages。
- `async_bridge.py` 连接 Qt 与 asyncio，不要将 UI 或 business behavior 移入此层。

新 configuration fields 必须接入 load 和 save。将 package construction 保持在这里或 desktop composition root；UI components 应通过 signals 通信。

参见 [desktop instructions](../AGENTS.md)。
