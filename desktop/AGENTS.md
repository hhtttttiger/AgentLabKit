# Desktop client

## Role

`desktop` is a standalone PySide6 client. It talks directly to the reusable package layer and does not depend on the FastAPI backend, frontend, Redis, or PostgreSQL.

## Boundaries

- `app/` is the composition root: create components, connect signals, and own shutdown.
- `core/` owns desktop configuration, package assembly, and the Qt/asyncio bridge.
- `ui/` emits Qt signals and must not call LLM, storage, or capture services directly.
- `tools/` contains desktop-specific tools; register new tools through its registry and keep filesystem access within the documented safety boundary.
- `capture/` owns screenshot selection and image analysis; keep it separate from UI composition.
- `storage/` owns local SQLite persistence; it is not the server memory/database layer.

Do not make desktop code depend on backend internals. Prefer `agent_runtime` and `llm_gateway` package protocols for text-agent behavior and preserve the local configuration/data paths.

## Key paths

- `main.py` — desktop entrypoint.
- `app/desktop_app.py` — composition and lifecycle.
- `core/` — configuration and runtime assembly.
- `tools/`, `capture/`, `storage/`, `ui/`, `utils/` — local subsystems.

## Verification

Run the relevant desktop tests when available. At minimum, import or execute the changed module with the desktop dependencies installed; do not use backend startup commands to validate desktop-only changes.

## References

- [Root instructions](../AGENTS.md)
- [Agent Runtime](../packages/agent_runtime/AGENTS.md)
- [LLM Gateway](../packages/llm_gateway/AGENTS.md)
