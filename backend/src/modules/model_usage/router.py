"""Model-usage monitoring API — model summaries, request logs, error logs.

Routes (mounted under /api/model-usage):
    GET /statistics/overview         — aggregated overview with per-model summaries
    GET /statistics/models           — per-model aggregated usage (paginated)
    GET /requests                    — per-request usage rows
    GET /errors                      — failed request rows
    GET /errors/distinct-error-codes — known error codes in the table
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from common.datetime_utils import parse_iso_datetime
from common.response import ok, paged
from .dependencies import ModelUsageServiceDep


router = APIRouter()


# ── shared query-parameter dependency ──────────────────────────────────────

async def _base_filters(
    from_: Annotated[str | None, Query(alias="from")] = None,
    to: str | None = Query(None),
    modelKey: str | None = Query(None),
) -> dict:
    return {
        "from_dt": parse_iso_datetime(from_),
        "to_dt": parse_iso_datetime(to),
        "model_key": modelKey,
    }


BaseFiltersDep = Annotated[dict, Depends(_base_filters)]


async def _paginated_filters(
    base: BaseFiltersDep,
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=200),
) -> dict:
    return {**base, "page": page, "page_size": pageSize}


PaginatedFiltersDep = Annotated[dict, Depends(_paginated_filters)]


# ── endpoints ──────────────────────────────────────────────────────────────

@router.get("/statistics/overview")
async def get_overview(
    svc: ModelUsageServiceDep,
    filters: BaseFiltersDep,
):
    result = await svc.get_overview(**filters)
    return ok(result.model_dump(mode="json"))


@router.get("/statistics/models")
async def list_model_summaries(
    svc: ModelUsageServiceDep,
    f: PaginatedFiltersDep,
):
    items, total = await svc.list_model_summaries(**f)
    return ok(paged([i.model_dump(mode="json") for i in items], total, f["page"], f["page_size"]))


@router.get("/errors/distinct-error-codes")
async def list_distinct_error_codes(
    svc: ModelUsageServiceDep,
):
    result = await svc.get_distinct_error_codes()
    return ok(result.model_dump(mode="json"))


@router.get("/requests")
async def list_requests(
    svc: ModelUsageServiceDep,
    f: PaginatedFiltersDep,
):
    items, total = await svc.list_requests(**f)
    return ok(paged([i.model_dump(mode="json") for i in items], total, f["page"], f["page_size"]))


@router.get("/errors")
async def list_errors(
    svc: ModelUsageServiceDep,
    f: PaginatedFiltersDep,
    errorCode: str | None = Query(None),
):
    items, total = await svc.list_errors(error_code=errorCode, **f)
    return ok(paged([i.model_dump(mode="json") for i in items], total, f["page"], f["page_size"]))
