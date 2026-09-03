# Long-term memory

`packages/memory` 负责 cross-session persistent memory，包括 storage、extraction、retrieval、injection、consolidation 和 provider selection。它不同于管理单个 session context window 的 `agent_runtime/memory`。

- 将 provider implementations 保持在 memory provider interfaces 后面。
- Native extraction 和 embeddings 使用 `llm_gateway`；不要直接调用 provider APIs。
- PostgreSQL/pgvector persistence 属于这里；Runtime 通过显式 composition/adapters 接收 memory behavior。
- Memory injection 丰富 Runtime-managed messages，但不拥有 Run、Trace 或 execution identity。

参见 [根目录 instructions](../../AGENTS.md)、[runtime session memory](../agent_runtime/src/agent_runtime/memory/AGENTS.md)，并运行 `packages/memory/tests/` 下的相关 tests。
