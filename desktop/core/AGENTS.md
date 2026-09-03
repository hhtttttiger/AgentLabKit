# Desktop core

`core` is the desktop foundation and must remain independent of other desktop subsystems.

- `config.py` owns `AppConfig`/`LLMConfig` persistence at `~/.config/agentlabkit/desktop.toml`.
- `bootstrap.py` assembles the reusable LLM/agent packages.
- `async_bridge.py` bridges Qt and asyncio without moving UI or business behavior into this layer.

New configuration fields must be wired through load and save. Keep package construction here or in the desktop composition root; UI components should communicate through signals.

See [desktop instructions](../AGENTS.md).