"""可观测性 API Router — Trace 列表、详情、时间线、统计。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Query

from common.response import ok, paged
from .dependencies import TraceStoreDep
from .schemas import (
    TraceListItem,
    TraceDetailResponse,
    SpanItem,
    TraceStatsResponse,
)

router = APIRouter()


def _to_trace_item(t) -> dict:
    return TraceListItem(
        trace_id=t.trace_id,
        root_span_id=t.root_span_id,
        agent_key=t.agent_key,
        session_id=t.session_id,
        status=t.status,
        total_duration_ms=t.total_duration_ms,
        total_input_tokens=t.total_input_tokens,
        total_output_tokens=t.total_output_tokens,
        total_estimated_cost=t.total_estimated_cost,
        span_count=t.span_count,
        started_at_utc=t.started_at_utc,
        completed_at_utc=t.completed_at_utc,
    ).model_dump()


def _to_span_item(s) -> dict:
    return SpanItem(
        span_id=s.span_id,
        trace_id=s.trace_id,
        parent_span_id=s.parent_span_id,
        span_kind=s.span_kind,
        name=s.name,
        status=s.status,
        started_at_utc=s.started_at_utc,
        completed_at_utc=s.completed_at_utc,
        duration_ms=s.duration_ms,
        attributes=s.attributes,
        error_code=s.error_code,
        error_message=s.error_message,
    ).model_dump()


@router.get("")
async def list_traces(
    store: TraceStoreDep,
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    agent_key: str | None = None,
    status: str | None = None,
    days: int | None = Query(None, ge=1, le=365),
):
    from_date = None
    to_date = None
    if days:
        to_date = datetime.now(timezone.utc)
        from_date = to_date - timedelta(days=days)

    traces, total = await store.list_traces(
        agent_key=agent_key,
        status=status,
        from_date=from_date,
        to_date=to_date,
        page=page,
        page_size=pageSize,
    )
    items = [_to_trace_item(t) for t in traces]
    return ok(paged(items, total, page, pageSize))


@router.get("/stats")
async def trace_stats(
    store: TraceStoreDep,
    days: int = Query(7, ge=1, le=365),
):
    to_date = datetime.now(timezone.utc)
    from_date = to_date - timedelta(days=days)
    stats = await store.get_stats(from_date=from_date, to_date=to_date)
    return ok(TraceStatsResponse(
        total_traces=int(stats.get("total_traces", 0)),
        avg_duration_ms=round(float(stats.get("avg_duration_ms", 0)), 1),
        total_tokens=int(stats.get("total_tokens", 0)),
        error_count=int(stats.get("error_count", 0)),
    ).model_dump())


@router.get("/{trace_id}")
async def get_trace_detail(
    trace_id: str,
    store: TraceStoreDep,
):
    trace = await store.get_trace(trace_id)
    if not trace:
        from common.errors import NotFoundError
        raise NotFoundError("Trace", trace_id)

    spans = await store.get_trace_spans(trace_id)
    return ok(TraceDetailResponse(
        trace=_to_trace_item(trace),
        spans=[_to_span_item(s) for s in spans],
    ).model_dump())


@router.get("/{trace_id}/timeline")
async def get_trace_timeline(
    trace_id: str,
    store: TraceStoreDep,
):
    """返回 waterfall 排序的 span 列表（按 started_at_utc 排序）。"""
    trace = await store.get_trace(trace_id)
    if not trace:
        from common.errors import NotFoundError
        raise NotFoundError("Trace", trace_id)
    spans = await store.get_trace_spans(trace_id)
    return ok([_to_span_item(s) for s in spans])
