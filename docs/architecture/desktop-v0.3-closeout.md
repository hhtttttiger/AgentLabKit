# AgentLab Desktop v0.3 Closeout

> Scope: this closeout applies only to the current Tauri client under
> `frontend/admin` and `frontend/admin/src-tauri`. The former PySide6 client is
> deprecated; see [`desktop/DEPRECATED.md`](../../desktop/DEPRECATED.md).
>
> Product composition follows [Desktop Product Projection](desktop-product-projection.md).

Status: **NOT SEALED**

This is the closeout record for the Cross-Agent Replay baseline. The repository
verification is complete, but the product baseline is not sealed until the
real-user acceptance loop is run with a configured Native Agent.

## Supported baseline

- Local project execution with Native Agent
- Run inspection and dataset capture
- Codex replay with source-run provenance
- Evaluation and evidence comparison
- Local SQLite mode without Docker, PostgreSQL, or Redis

## Verification record

- Local API health and Agent catalog: passed; Native Agent and Codex were detected.
- Desktop/application targeted tests: 106 passed.
- Frontend type check: passed.
- Frontend tests: 107 files, 393 assertions passed.
- Frontend production build: passed.
- Tauri `cargo check`: passed.
- Real three-case Native → Case → Codex Replay → Evaluation → Compare loop: **not run**.

## Blocking acceptance gap

The closeout environment has no configured `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`,
or `AGENTLAB_LLM_API_KEY`. Therefore a real Native Agent Run A cannot be
executed without inventing data, so product-loop, restart-persistence, and
cross-agent asset-continuity acceptance remain unverified.

## Known limitations accepted by v0.3 scope

- Codex is the only external agent.
- Replay preserves an absolute workspace path; moved projects fail explicitly.
- Workspace containment is not an OS sandbox.
- Codex authentication is owned by the Codex CLI.
- Python is not bundled as a standalone Desktop distribution.
- Knowledge local vector capability remains Server Mode only.
- Local API port allocation still has a small reserve → spawn race; readiness
  detects failure but does not automatically retry.

## Observed product friction

No real-user friction ranking is recorded because the required real scenarios
were not executed.
