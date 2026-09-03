# Retrieval

`retrieval` is the sole RAG capability package: document processing, splitting, embeddings, vector/full-text search, and GraphRAG abstractions. Business modules should use its interfaces and provide adapters for application storage and gateway access.

- Do not implement document processing, embeddings, or vector search in backend modules.
- Keep embedding and vector-store providers behind the existing interfaces.
- Graph search remains explicit; do not silently merge it into ordinary search.
- Keep the local document pipeline stateless and reusable.

See [root instructions](../../AGENTS.md) and run `python3 -m pytest packages/retrieval/tests -q` after retrieval changes.