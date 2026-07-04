---
name: local-dev
description: "Start local dev environment (Docker infra + local backend + local frontend). Use when user wants to run/debug the project locally."
trigger: /local-dev
---

# /local-dev

Start the full local development environment: Docker infrastructure + local Python backend + local Vite frontend.

Infra (postgres/redis) is **persistent** — it survives `colima`/host restarts and keeps its data across sessions (named volumes `pgdata`/`redisdata` + `restart: unless-stopped`). A normal invocation is a fast **resume**: infra is already up, migration/seed are no-ops, only backend/frontend get (re)started. To wipe everything and start clean, run `make reset` first (then `/local-dev` re-seeds).

## Architecture

```
Frontend (Vite, first free port from 5173) ──▶ Backend (Uvicorn :8000)
                                                     │
                                              ┌──────┴──────┐
                                              │   Docker    │
                                              │ PostgreSQL  │ :5432  (volume: pgdata)
                                              │ Redis       │ :6379  (volume: redisdata)
                                              └─────────────┘
```

Worker 是独立消费进程(`make worker`),通过 Redis Streams 接收 backend enqueue 的文档索引消息,运行分块 + embedding + 向量存储 pipeline。没有 worker,新建文档会停在 `Pending` 索引状态。

## Prerequisites

- Colima must be available (`make up` auto-starts it if stopped).
- `make` — used for the infra lifecycle (`make up` / `stop` / `reset` / `status` / `logs`).

## Steps

Execute in order. Each step must succeed before proceeding.

### 1. Start / resume Docker infrastructure

```bash
make up        # starts postgres + redis, waits for healthy, auto-starts colima if needed
```

On a **resume** this returns in ~1s and keeps existing data. Only after `make reset` (or a brand-new checkout) is the DB empty, in which case step 2 will re-seed.

Verify:

```bash
make status    # or: docker compose ps
```

Expected: `postgres` and `redis` both show `(healthy)`.

### 2. Start Backend

Check if `backend/.venv` exists. If not, create it and install dependencies:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ../packages/db -e ../packages/infra -e ../packages/retrieval \
            -e ../packages/cost_analysis -e ../packages/observability \
            -e ../packages/memory -e ../packages/evaluation \
            -e ../packages/llm_gateway -e ../packages/agent_runtime \
            -e ".[dev]" 'bcrypt<4.1'
```

**If the backend already serves health, skip to step 3** (resume):

```bash
curl -s http://localhost:8000/health
```

Otherwise, apply migrations (idempotent — no-op when already at head):

```bash
cd backend
source .venv/bin/activate
PYTHONPATH=src:../packages/llm_gateway/src:../packages/agent_runtime/src alembic upgrade head
```

Seed default data **only if the DB isn't seeded yet** (bootstrap is idempotent, but this skips the bcrypt noise on resume). Check the `auth_users` table:

```bash
docker compose exec -T postgres psql -U app -d agentlabkit -tAc "select count(*) from auth_users"
```

If the count is `0`, run the seed:

```bash
cd backend
source .venv/bin/activate
PYTHONPATH=src:../packages/llm_gateway/src:../packages/agent_runtime/src python -m bootstrap
```

Start the backend server in the background:

```bash
cd backend
source .venv/bin/activate
PYTHONPATH=src:../packages/llm_gateway/src:../packages/agent_runtime/src uvicorn main:create_app --factory --host 0.0.0.0 --port 8000 --reload
```

Verify:

```bash
curl -s http://localhost:8000/health
```

Expected: `{"success":true,"msg":"ok","data":{"status":"healthy"}}`

### 2b. Start Worker (document-indexing consumer)

The backend only **enqueues** document processing; a separate worker process
consumes the queue and runs the indexing pipeline (chunking + embedding + vector
store). Without it, new documents stay in `Pending` index state forever. Start it
in a second terminal or background:

```bash
cd backend
source .venv/bin/activate
PYTHONPATH=src:../packages/llm_gateway/src:../packages/agent_runtime/src python -m worker
```

Verify the log shows:

```
Consumer doc-worker-<host> started on document_processing (concurrency=3)
Worker ready, waiting for messages (Ctrl-C to stop)
```

(Prerequisite: `APP_RETRIEVAL__ENABLED=true` and `APP_REDIS__ENABLED=true` in `.env`.)

### 3. Start Frontend

```bash
cd frontend/admin
npm install
```

Pick the **first free port from 5173** (5173 is often already taken by another dev server):

```bash
for p in 5173 5174 5175 5176 5177; do
  lsof -nP -iTCP:$p -sTCP:LISTEN >/dev/null 2>&1 || { PORT=$p; break; }
done
npm run dev -- --port $PORT
```

Read the Vite output to confirm the actual port, then verify `http://localhost:$PORT/` returns HTTP 200.

### 4. Report Status

Report the actual bound ports:

| Service | URL | Status |
|---------|-----|--------|
| Frontend | http://localhost:$PORT/ | ✅ |
| Backend API | http://localhost:8000/health | ✅ |
| Worker | (no HTTP; logs to its terminal) | ✅ |
| PostgreSQL | localhost:5432 | ✅ |
| Redis | localhost:6379 | ✅ |

Default credentials: `admin / admin`

## Infra lifecycle (postgres + redis are persistent)

| Command | Effect |
|---------|--------|
| `make up` | Start/resume — data kept, ~1s on resume |
| `make stop` | Pause containers — data kept, fast resume |
| `make status` | Show container health |
| `make reset` | ⚠️ Wipe containers **and data volumes** — clean slate |
| `make logs` | Tail postgres/redis logs (Ctrl-C to exit) |
| `make worker` | Start the document-indexing worker (local process, Ctrl-C to stop) |

Backend + frontend are local processes (uvicorn/vite); they are **not** part of the persistent Docker stack — use `/local-dev` to (re)start them. To end a session cleanly without losing data, use `make stop` (not `docker compose down`).

## Important Notes

- **Local dev URL is `/`**, not `/admin/` (that's Docker mode only)
- Backend uses `--reload` for auto-restart on code changes
- Frontend Vite HMR updates instantly on save
- Infra survives `colima stop`/host reboot — on next `colima start` the containers come back automatically (`restart: unless-stopped`)
- `.env` at project root configures backend (DB, JWT, etc.)
- `frontend/admin/.env.local` configures API proxy target (points to backend 8000, independent of the frontend port)
- If JWT 401 errors occur, check that `jwt.decode()` in `common/auth.py` passes `audience=` parameter
- **PYTHONPATH must include** `src:../packages/llm_gateway/src:../packages/agent_runtime/src` for backend **and worker** commands
- **Worker must be running** for document indexing; without it, new documents stay `Pending`. Start via `make worker` or `python -m worker` (same PYTHONPATH as backend)
- Bash tool working directory persists across calls — always include `cd <target>` when switching between `backend/` and `frontend/admin/`, even if a previous step already `cd`'d there
- First-time bootstrap may show a harmless bcrypt version warning (`passlib` compatibility with `bcrypt>=4.1`). If `bcrypt<4.1` is pinned during venv setup (see step 2), this is silenced entirely
