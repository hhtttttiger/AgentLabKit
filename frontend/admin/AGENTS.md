# Admin frontend

## Role

`frontend/admin` is the React 19 + TypeScript client of the public FastAPI HTTP/SSE contract. It owns presentation, client state, routing, and API-to-view-model mapping; it does not own backend execution semantics.

## Contract rules

- Keep HTTP calls and response mapping in `src/shared/api` or the module API layer; do not scatter raw requests through views.
- `Run != Trace`. Trace is observability data and must not be used to reconstruct a Run.
- Never invent or fall back for `runId`, `traceId`, timestamps, terminal status, or other authoritative execution fields. Missing values render as unavailable.
- Preserve nullable evaluation verdicts and legitimate `score = 0` values.
- Consume the public SSE contract (`type`, `data`, `runId`, terminal events, `[DONE]`); do not expose or depend on internal RuntimeEvent taxonomy.
- Keep the `app / shared / modules` layout. Register modules through `src/app/modules.tsx`; keep resource-specific API, hooks, types, and UI together.

## Key paths

- `src/app/` — application shell and routing.
- `src/shared/api/` — HTTP client, contracts, errors, and query setup.
- `src/shared/agent-trace/` — shared Trace presentation contracts/components.
- `src/modules/` — feature modules, including `runs`, `evaluation`, `ai-chat`, and management resources.

## Verification

From `frontend/admin/`:

```bash
npm run check
npm run test
npm run build
```

## References

- [Root instructions](../../AGENTS.md)
- [FastAPI adapter boundary](../../docs/architecture/fastapi-adapter-boundary.md)
- [Execution Model v2](../../docs/architecture/execution-model-v2.md)
