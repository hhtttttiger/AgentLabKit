<!-- Parent: ../../AGENTS.md -->
# Runtime guardrails

Guardrails 是供 `AgentRuntime` 使用的 composable input、output 和 tool middleware。

- `PASS`、`MODIFY` 和 `BLOCK` 是不同 outcomes。MODIFY result 必须提供 replacement text；BLOCK result 必须提供 reason。
- BLOCK 通常表示有效的 business outcome。Run 仍会终止；不要将其变成 unhandled Runtime crash。
- 保留 guard ordering 和 short-circuit behavior。通过 factory extension point 注册可扩展 guards。
- 保持 guardrails 独立于 provider-specific APIs 和 Runtime internals。

变更后在 `packages/agent_runtime/tests/` 运行 targeted guardrail tests。参见 [agent_runtime instructions](../../../AGENTS.md)。
