# Long-term memory

`packages/memory` owns cross-session persistent memory, including storage, extraction, retrieval, injection, consolidation, and provider selection. It is distinct from `agent_runtime/memory`, which manages one session’s context window.

- Keep provider implementations behind the memory provider interfaces.
- Native extraction and embeddings use `llm_gateway`; do not call provider APIs directly.
- PostgreSQL/pgvector persistence belongs here; Runtime receives memory behavior through explicit composition/adapters.
- Memory injection enriches Runtime-managed messages but does not own Run, Trace, or execution identity.

See [root instructions](../../AGENTS.md), [runtime session memory](../agent_runtime/src/agent_runtime/memory/AGENTS.md), and run relevant tests under `packages/memory/tests/`.