from __future__ import annotations

import asyncio
from pathlib import Path

import httpx

from agent_runtime import ToolExecutionContext
from desktop.local.composition import create_local_app
from desktop.tools.bash import BashTool
from desktop.tools.filesystem import resolve_workspace_path


def test_workspace_path_containment_resolves_symlinks(tmp_path: Path) -> None:
    workspace = (tmp_path / "workspace").resolve()
    workspace.mkdir()
    (workspace / "src").mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("outside", encoding="utf-8")
    (workspace / "link").symlink_to(outside)

    assert resolve_workspace_path("src", workspace) == workspace / "src"
    for requested in ("../outside.txt", str(outside), "link"):
        try:
            resolve_workspace_path(requested, workspace)
        except ValueError:
            continue
        raise AssertionError(f"path escaped workspace: {requested}")


def test_shell_cwd_is_contained_in_workspace(tmp_path: Path) -> None:
    workspace = (tmp_path / "workspace").resolve()
    (workspace / "packages").mkdir(parents=True)
    context = ToolExecutionContext(
        session_id="session",
        trace_id="trace",
        metadata={"working_directory": str(workspace)},
    )

    result = asyncio.run(BashTool().execute({"command": "pwd", "working_directory": "packages"}, context))
    assert result.status == "success"
    assert str(workspace / "packages") in result.output

    escaped = asyncio.run(BashTool().execute({"command": "pwd", "working_directory": "../"}, context))
    assert escaped.status == "error"


def test_local_api_requires_ephemeral_token(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("AGENTLAB_LOCAL_TOKEN", "test-token")
    app = create_local_app(tmp_path / "agentlab.db")

    async def exercise() -> None:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            assert (await client.get("/health")).status_code == 200
            assert (await client.get("/api/runs")).status_code == 401
            assert (await client.get("/api/runs", headers={"X-AgentLab-Local-Token": "wrong"})).status_code == 401
            assert (await client.get("/api/runs", headers={"X-AgentLab-Local-Token": "test-token"})).status_code == 200

    try:
        asyncio.run(exercise())
    finally:
        app.state.local.db.close()
