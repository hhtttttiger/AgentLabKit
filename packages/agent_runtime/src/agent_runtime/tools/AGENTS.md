# Runtime tools

This subtree owns dynamic tool registration, per-agent filtering, schema validation, timeout/retry isolation, and the compatibility `ToolRegistry` wrapper.

- New code should use `DynamicToolRegistry`; preserve the public compatibility wrapper for existing callers.
- `auto_only`, `whitelist`, and `disabled` invocation modes must retain their current meaning.
- Tool failures are structured `ToolResult.error` values, not exceptions escaping `ToolExecutor`.
- Keep external-tool support behind the existing handler protocol; do not add network assumptions to the core protocol.

Run the relevant dynamic-tool and runtime tests under `packages/agent_runtime/tests/`. See [agent_runtime instructions](../../../AGENTS.md).