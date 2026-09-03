<!-- Parent: ../../AGENTS.md -->
# Runtime tools

此 subtree 负责 dynamic tool registration、per-agent filtering、schema validation、timeout/retry isolation，以及兼容性的 `ToolRegistry` wrapper。

- 新代码应使用 `DynamicToolRegistry`；为现有 callers 保留 public compatibility wrapper。
- `auto_only`、`whitelist` 和 `disabled` invocation modes 必须保持现有含义。
- Tool failures 是结构化的 `ToolResult.error` values，不是从 `ToolExecutor` 逸出的 exceptions。
- 将 external-tool support 保持在现有 handler protocol 后面；不要为 core protocol 增加 network assumptions。

在 `packages/agent_runtime/tests/` 下运行相关 dynamic-tool 和 runtime tests。参见 [agent_runtime instructions](../../../AGENTS.md)。
