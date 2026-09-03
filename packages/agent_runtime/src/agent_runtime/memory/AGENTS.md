# Runtime session memory

This subtree manages single-session context: token-aware trimming, optional summarization, message priority, and session snapshots. It is distinct from the cross-session `packages/memory` package.

- Keep context preparation as a pre-execution layer; it must not own execution identity.
- Preserve the disabled-memory fallback behavior and summary metadata markers.
- Add durable stores behind the `SessionStore` protocol; do not make the in-memory implementation depend on database infrastructure.
- Use `llm_gateway` through its protocol for summarization.

Run the relevant memory and runtime tests under `packages/agent_runtime/tests/`. See [agent_runtime instructions](../../../AGENTS.md).