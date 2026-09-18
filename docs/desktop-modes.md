# AgentLab Desktop modes

The Tauri client supports two runtime modes. The mode is read when the app
starts, so restart the client after changing the configuration.

## Local mode

Local mode is the default. Tauri starts `desktop.local.server`, which uses the
user's SQLite database and in-process queue/event primitives. It does not need
PostgreSQL, Redis, Docker, or an external worker.

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
