from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from agent_runtime.contracts.run import AgentRun, RunTarget
from application.execution.replay_external import (
    ExternalReplayWorkspaceUnavailable,
    ReplayExternalRun,
    ReplayExternalRunCommand,
)
from application.execution.run_projection import RunRecord
from desktop.local.composition import LocalExecutor


class SourceRuns:
    def __init__(self, record: RunRecord):
        self.record = record

    async def get_run(self, _run_id: str):
        return self.record


class RecordingExternal:
    def __init__(self):
        self.kwargs = None

    async def execute(self, **kwargs):
        self.kwargs = kwargs
        return AgentRun(run_id="new", input=kwargs["input"], target=kwargs["target"])


def test_replay_workspace_comes_from_source_run_not_caller_metadata(tmp_path: Path) -> None:
    source = RunRecord(run_id="source", input="task", metadata={"working_directory": str(tmp_path)})
    executor = RecordingExternal()

    result = asyncio.run(ReplayExternalRun(SourceRuns(source), executor).execute(
        ReplayExternalRunCommand(
            source_run_id="source", agent_id="codex",
            metadata={"working_directory": str(tmp_path / "caller-redirect")},
        )
    ))

    assert result.run.run_id == "new"
    assert executor.kwargs["working_directory"] == str(tmp_path.resolve())
    assert executor.kwargs["metadata"]["working_directory"] == str(tmp_path.resolve())


@pytest.mark.parametrize("metadata", [{}, {"working_directory": "/definitely/missing"}])
def test_replay_missing_source_workspace_is_explicit(metadata) -> None:
    source = RunRecord(run_id="source", input="task", metadata=metadata)
    with pytest.raises(ExternalReplayWorkspaceUnavailable, match="replay workspace"):
        asyncio.run(ReplayExternalRun(SourceRuns(source), RecordingExternal()).execute(
            ReplayExternalRunCommand(source_run_id="source", agent_id="codex")
        ))


class FakeRuntime:
    def __init__(self):
        self.calls = []

    async def run(self, request):
        self.calls.append(request)
        return AgentRun(run_id="native", input=request.user_message, target=RunTarget(kind="native", agent_key="local-agent"))


class FakeExternal:
    def __init__(self):
        self.calls = []

    async def execute(self, **kwargs):
        self.calls.append(kwargs)
        return AgentRun(run_id="external", input=kwargs["input"], target=RunTarget(kind="external", agent_key="codex"))


def test_local_executor_dispatches_by_catalog_kind() -> None:
    runtime = FakeRuntime()
    external = FakeExternal()
    executor = LocalExecutor(runtime, external)

    native = asyncio.run(executor.execute(
        input="native", target=RunTarget(kind="native", agent_key="local-agent"),
        session_id=None, user_id=None, history=(), metadata={},
    ))
    external_run = asyncio.run(executor.execute(
        input="external", target=RunTarget(kind="external", agent_key="codex"),
        session_id=None, user_id=None, history=(), metadata={"working_directory": "/tmp"},
    ))

    assert native.run_id == "native"
    assert external_run.run_id == "external"
    assert len(runtime.calls) == 1
    assert len(external.calls) == 1


def test_local_executor_rejects_unsupported_external_agent() -> None:
    with pytest.raises(ValueError, match="unsupported external agent"):
        asyncio.run(LocalExecutor(FakeRuntime(), FakeExternal()).execute(
            input="task", target=RunTarget(kind="external", agent_key="other"),
            session_id=None, user_id=None, history=(), metadata={"working_directory": "/tmp"},
        ))
