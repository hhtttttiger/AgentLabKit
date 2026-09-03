# Desktop tools

Desktop tools 通过 `create_desktop_tool_registry()` 注册，并使用 `agent_runtime` tool protocols（`ToolSpec`、handler 和 result）。保持 tool definitions 与 Runtime 分离，并在 `registry.py` 注册新 tools。

保留 filesystem safety boundary：file operations 限制在 user home directory。Shell execution 必须 opt-in，且默认保持 disabled。Tool handlers 应返回结构化的 `ToolResult` values，避免依赖 desktop UI components。

参见 [desktop instructions](../AGENTS.md) 和 [Agent Runtime](../../packages/agent_runtime/AGENTS.md)。
