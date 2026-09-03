from __future__ import annotations

from fastapi import APIRouter

from application import ReplayRunCommand
from application.execution.replay_run import (
    ReplayInputUnavailable,
    ReplaySourceNotFound,
    ReplayTargetUnavailable,
    ReplayTargetUnsupported,
)
from common.auth import CurrentUser
from common.errors import BusinessError, ConflictError, NotFoundError
from common.response import ok

from .dependencies import ReplayRunDep, RunReaderDep
from .schemas import (
    ReplayRunRequest,
    ReplayRunResponse,
    ReplayRunResponseEnvelope,
    RunResponseEnvelope,
    to_run_response,
)

router = APIRouter()


@router.get(
    "/{run_id}",
    response_model=RunResponseEnvelope,
    responses={404: {"description": "Run not found"}},
)
async def get_run(run_id: str, reader: RunReaderDep):
    run = await reader.get_run(run_id)
    if run is None:
        raise NotFoundError("Run", run_id)
    return ok(to_run_response(run).model_dump())


@router.post(
    "/{run_id}/replay",
    response_model=ReplayRunResponseEnvelope,
    responses={404: {"description": "Source Run not found"}, 409: {"description": "Historical target unavailable"}},
)
async def replay_run(
    run_id: str,
    replay: ReplayRunDep,
    current_user: CurrentUser,
    body: ReplayRunRequest | None = None,
):
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
        run=to_run_response(result.run),
    ).model_dump())
