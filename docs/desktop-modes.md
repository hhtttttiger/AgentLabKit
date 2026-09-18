# AgentLab Desktop modes

The Tauri client supports two runtime modes. The mode is read when the app
starts, so restart the client after changing the configuration.

## Local mode

Local mode is the default. Tauri starts `desktop.local.server`, which uses the
user's SQLite database and in-process queue/event primitives. It does not need
PostgreSQL, Redis, Docker, or an external worker.

Tauri owns the Local API lifecycle. At startup it allocates an available
`127.0.0.1` port, creates an ephemeral process token, starts Python with
`AGENTLAB_LOCAL_PORT` and `AGENTLAB_LOCAL_TOKEN`, then polls `/health` with a
bounded timeout before publishing the frontend runtime configuration. The
frontend sends `X-AgentLab-Local-Token` on every `/api/*` request. `/health` is
intentionally available without the token for readiness checks.

### 当前开发限制

Tauri 目前直接启动系统 `python3`，仓库还没有独立的 Desktop installer 或
Desktop requirements lock。Local Mode 使用的 active desktop tools 仍会从
`desktop.tools.registry` 加载 clipboard/screen 工具，而这些模块当前依赖
PySide6；因此运行 Local Mode 的 Python 环境必须同时具备 package 依赖和
PySide6。这个依赖是旧桌面工具尚未完全解耦的过渡性限制，不代表旧 PySide6
外壳仍是产品入口。Server Mode 不启动这套本地 Python 进程。

Each Local Mode execution with a selected workspace canonicalizes that
directory once and passes it to the Runtime as `metadata.working_directory`.
Desktop file tools and shell cwd validation resolve paths before checking
containment, so `..`, absolute outside paths, and symlink escapes are rejected.
Workspace containment reduces accidental filesystem escape; it is not an OS
security sandbox and does not restrict command contents.

The Local Mode lifecycle is deliberately bounded to `start → ready → use →
shutdown`. It does not provide auto-restart, a watchdog, a daemon, persistent
authentication, or a permission framework. Server mode remains unchanged.

## Server mode

Server mode does not start the embedded Python process. The client sends API
requests to the configured FastAPI server, which keeps the normal PostgreSQL,
Redis Streams, worker, and server-side finalization composition.

The runtime configuration file is `config.json` in the Tauri application
configuration directory. Its contents are:

```json
{
  "mode": "server",
  "serverUrl": "https://agentlab.example.com"
}
```

`mode` accepts `local` or `server`. Missing or invalid values fall back to
`local`. For development and CI, environment variables override the file:

```bash
AGENTLAB_MODE=server AGENTLAB_SERVER_URL=http://127.0.0.1:9000 npm run desktop:dev
```

`AGENTLAB_SERVER_URL` takes precedence over `VITE_API_BASE_URL`. The browser
client remains server-oriented and continues to use `VITE_API_BASE_URL`.
