# Retrieval

`retrieval` 是唯一的 RAG capability package：负责 document processing、splitting、embeddings、vector/full-text search 和 GraphRAG abstractions。Business modules 应使用其 interfaces，并为 application storage 和 gateway access 提供 adapters。

- 不要在 backend modules 中实现 document processing、embeddings 或 vector search。
- 将 embedding 和 vector-store providers 保持在现有 interfaces 后面。
- Graph search 保持显式；不要将其静默合并到 ordinary search。
- 保持 local document pipeline 无状态且可复用。

参见 [根目录 instructions](../../AGENTS.md)，retrieval 变更后运行 `python3 -m pytest packages/retrieval/tests -q`。
