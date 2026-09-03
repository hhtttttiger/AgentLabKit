from __future__ import annotations

from fastapi import APIRouter

from common.errors import NotFoundError
from common.response import ok

from .dependencies import RunReaderDep
from .schemas import RunResponseEnvelope, to_run_response

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
