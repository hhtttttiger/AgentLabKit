from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from application import ReplayRun
from application.execution.run_projection import RunReader
from application_adapters.agent_runtime import AgentRuntimeExecutor, BackendAgentReader


def get_run_reader(request: Request) -> RunReader:
    reader = getattr(request.app.state, "run_reader", None)
    if reader is None:
        raise RuntimeError("RunReader not initialized — check lifespan wiring")
    return reader


RunReaderDep = Annotated[RunReader, Depends(get_run_reader)]


def get_replay_run(request: Request) -> ReplayRun:
    reader = get_run_reader(request)
    runtime = getattr(request.app.state, "agent_runtime", None)
    loader = getattr(request.app.state, "agent_definition_loader", None)
    if runtime is None or loader is None:
        raise RuntimeError("Agent runtime is not initialized")
    return ReplayRun(
        runs=reader,
        executor=AgentRuntimeExecutor(runtime),
        targets=BackendAgentReader(loader),
    )


ReplayRunDep = Annotated[ReplayRun, Depends(get_replay_run)]
