# Runtime guardrails

Guardrails are composable input, output, and tool middleware used by `AgentRuntime`.

- `PASS`, `MODIFY`, and `BLOCK` are distinct outcomes. A MODIFY result must provide replacement text; a BLOCK result must provide a reason.
- BLOCK normally represents a valid business outcome. The Run still terminates; do not turn it into an unhandled Runtime crash.
- Preserve guard ordering and short-circuit behavior. Register extensible guards through the factory extension point.
- Keep guardrails independent of provider-specific APIs and Runtime internals.

Run the targeted guardrail tests in `packages/agent_runtime/tests/` after changes. See [agent_runtime instructions](../../../AGENTS.md).