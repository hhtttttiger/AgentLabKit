from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

from desktop.local.external_agent import ExternalAgentRunner, detect_codex
from agent_runtime.contracts.run import RunTarget


def test_detect_codex_reports_missing_binary() -> None:
    result = detect_codex(which=lambda _name: None)
    assert result.agent_id == "codex"
    assert result.kind == "external"
    assert result.availability == "not_installed"


def test_external_runner_normalizes_jsonl_output(tmp_path: Path) -> None:
    script = tmp_path / "fake-codex"
    script.write_text(
        "#!/usr/bin/env python3\n"
        "import json, sys\n"
        "print(json.dumps({'type': 'item.completed', 'item': {'type': 'agent_message', 'text': 'done'}}))\n"
        "print(json.dumps({'type': 'turn.completed'}))\n",
        encoding="utf-8",
    )
    script.chmod(0o755)

    async def run():
        return await ExternalAgentRunner(executable=str(script)).execute(
            input="fix it", target=RunTarget(agent_key="codex"), working_directory=tmp_path,
        )

    result = asyncio.run(run())
    assert result.status.value == "completed"
    assert result.output == "done"
    assert result.metadata["execution_kind"] == "external"
    assert len(result.metadata["external_events"]) == 2
    assert result.target.agent_key == "codex"


def test_external_runner_preserves_process_failure(tmp_path: Path) -> None:
    script = tmp_path / "fake-codex-failure"
    script.write_text(
        "#!/usr/bin/env python3\n"
        "import sys\n"
        "print('bad news', file=sys.stderr)\n"
        "raise SystemExit(7)\n",
        encoding="utf-8",
    )
    script.chmod(0o755)

    async def run():
        return await ExternalAgentRunner(executable=str(script)).execute(
            input="fail", target=RunTarget(agent_key="codex"), working_directory=tmp_path,
        )

    result = asyncio.run(run())
    assert result.status.value == "failed"
    assert result.error is not None
    assert result.error.code == "external_process_failed"
    assert "bad news" in result.error.message


def test_external_runner_requires_existing_workspace(tmp_path: Path) -> None:
    async def run():
        return await ExternalAgentRunner(executable=sys.executable).execute(
            input="nope", target=RunTarget(agent_key="codex"), working_directory=tmp_path / "missing",
        )

    with pytest.raises(ValueError, match="working directory does not exist"):
        asyncio.run(run())
