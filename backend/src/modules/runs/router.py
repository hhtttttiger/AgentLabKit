from __future__ import annotations

from fastapi import APIRouter

from application import ReplayRunCommand, CaptureRunAsDatasetExampleCommand
from application.dataset.save_run_as_example import CaptureSourceRunNotFound, RunNotCapturable
from modules.evaluation.dependencies import CaptureRunAsDatasetExampleDep
from modules.evaluation.schemas import (
    CaptureRunRequest,
    CaptureRunResponse,
    CaptureRunResponseEnvelope,
)
from application.execution.replay_run import (
    ReplayInputUnavailable,
    ReplaySourceNotFound,
    ReplayTargetUnavailable,
    ReplayTargetUnsupported,
)
from common.auth import CurrentUser
from common.errors import BusinessError, ConflictError, NotFoundError
from common.response import ok

from .dependencies import ReplayRunDep, RunReaderDep, ensure_run_access
from .schemas import (
    agent_run_to_response,
    run_record_to_response,
    ReplayRunRequest,
    ReplayRunResponse,
    ReplayRunResponseEnvelope,
    RunResponseEnvelope,
)

router = APIRouter()


@router.post(
    "/{run_id}/capture",
    response_model=CaptureRunResponseEnvelope,
    responses={404: {"description": "Run or Dataset not found"}, 409: {"description": "Run is not capturable"}},
)
async def capture_run(
    run_id: str,
    body: CaptureRunRequest,
    capture: CaptureRunAsDatasetExampleDep,
    reader: RunReaderDep,
    current_user: CurrentUser,
):
    source = await reader.get_run(run_id)
    if source is None:
        raise NotFoundError("Run", run_id)
    ensure_run_access(source, current_user)
    try:
        result = await capture.execute(CaptureRunAsDatasetExampleCommand(
            dataset_id=str(body.dataset_id), run_id=run_id,
            expected_output=body.expected_output, metadata=body.metadata,
        ))
    except CaptureSourceRunNotFound:
        raise NotFoundError("Run", run_id)
    except RunNotCapturable as exc:
        raise ConflictError(str(exc))
    return ok(CaptureRunResponse(
        dataset_id=result.dataset_id,
        source_run_id=result.source_run_id,
        example_id=result.example_id,
    ).model_dump())


@router.get(
    "/{run_id}",
    response_model=RunResponseEnvelope,
    responses={404: {"description": "Run not found"}},
)
async def get_run(run_id: str, reader: RunReaderDep, current_user: CurrentUser):
    run = await reader.get_run(run_id)
    if run is None:
        raise NotFoundError("Run", run_id)
    ensure_run_access(run, current_user)
    return ok(run_record_to_response(run).model_dump())


@router.post(
    "/{run_id}/replay",
    response_model=ReplayRunResponseEnvelope,
    responses={404: {"description": "Source Run not found"}, 409: {"description": "Historical target unavailable"}},
)
async def replay_run(
    run_id: str,
    replay: ReplayRunDep,
    reader: RunReaderDep,
    current_user: CurrentUser,
    body: ReplayRunRequest | None = None,
):
    source = await reader.get_run(run_id)
    if source is None:
        raise NotFoundError("Run", run_id)
    ensure_run_access(source, current_user)

    try:
        result = await replay.execute(ReplayRunCommand(
            source_run_id=run_id,
            user_id=current_user["user_id"],
            metadata=(body.metadata if body is not None else {}),
        ))
    except ReplaySourceNotFound:
        raise NotFoundError("Run", run_id)
    except ReplayTargetUnavailable as exc:
        raise ConflictError(str(exc))
    except ReplayTargetUnsupported as exc:
        raise BusinessError(str(exc), status_code=422)
    except ReplayInputUnavailable as exc:
        raise BusinessError(str(exc), status_code=422)

    return ok(ReplayRunResponse(
        source_run_id=result.source_run_id,
        run=agent_run_to_response(result.run),
    ).model_dump())
