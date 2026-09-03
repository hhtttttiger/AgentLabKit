# Desktop tools

Desktop tools are registered through `create_desktop_tool_registry()` and use the `agent_runtime` tool protocols (`ToolSpec`, handler, and result). Keep tool definitions separate from the runtime and register new tools in `registry.py`.

Preserve the filesystem safety boundary: file operations are restricted to the user home directory. Shell execution is opt-in and must remain disabled by default. Tool handlers should return structured `ToolResult` values and avoid depending on desktop UI components.

See [desktop instructions](../AGENTS.md) and [Agent Runtime](../../packages/agent_runtime/AGENTS.md).