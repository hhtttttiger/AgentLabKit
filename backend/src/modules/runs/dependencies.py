from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from application import CaptureRunAsDatasetExample, ReplayRun
from application.execution.run_projection import RunReader, RunRecord
from common.errors import NotFoundError
from application_adapters.agent_runtime import AgentRuntimeExecutor, BackendAgentReader


def get_capture_run_as_dataset_example(request: Request) -> CaptureRunAsDatasetExample:
    use_case = getattr(request.app.state, "capture_run_as_dataset_example", None)
    if use_case is None:
        raise RuntimeError("CaptureRunAsDatasetExample not initialized — check lifespan wiring")
    return use_case


CaptureRunAsDatasetExampleDep = Annotated[
    CaptureRunAsDatasetExample, Depends(get_capture_run_as_dataset_example)
]


def get_run_reader(request: Request) -> RunReader:
    reader = getattr(request.app.state, "run_reader", None)
    if reader is None:
        raise RuntimeError("RunReader not initialized — check lifespan wiring")
    return reader


RunReaderDep = Annotated[RunReader, Depends(get_run_reader)]


def ensure_run_access(run: RunRecord, current_user: dict) -> None:
    """Enforce the Run resource boundary using only persisted Run ownership.

    Null ownership is deliberately denied, including legacy rows.  This helper
    returns 404 for mismatches to avoid disclosing another user's run.
    """
    if run.user_id is None or run.user_id != current_user["user_id"]:
        raise NotFoundError("Run", run.run_id)


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
