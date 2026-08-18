"""Observability V2 API: cursor pagination, trace tree and ingestion health."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Query, Request

from common.response import ok
from observability import TRACE_QUEUE_NAME

from .dependencies import ObservabilityModuleDep, TraceStoreDep
from .schemas import (
    IngestionHealthResponse,
    SpanItem,
    TraceDetailResponse,
    TraceListItem,
    TracePageResponse,
    TraceStatsResponse,
)

router = APIRouter()


def _to_trace_item(trace) -> TraceListItem:
    return TraceListItem.model_validate(trace, from_attributes=True)


def _to_span_item(span) -> SpanItem:
    return SpanItem.model_validate(span, from_attributes=True)


@router.get("")
async def list_traces(
    store: TraceStoreDep,
    cursor: str | None = None,
    limit: int = Query(20, ge=1, le=100),
    agent_key: str | None = None,
    session_id: str | None = None,
    status: str | None = None,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
):
    page = await store.list_traces(
        agent_key=agent_key,
        session_id=session_id,
        status=status,
        from_date=from_date,
        to_date=to_date,
        cursor=cursor,
        limit=limit,
    )
    return ok(
        TracePageResponse(
            items=[_to_trace_item(item) for item in page.items],
            next_cursor=page.next_cursor,
        ).model_dump(),
    )


@router.get("/stats")
async def trace_stats(
    store: TraceStoreDep,
    days: int = Query(7, ge=1, le=365),
):
    to_date = datetime.now(timezone.utc)
    stats = await store.get_stats(
        from_date=to_date - timedelta(days=days),
        to_date=to_date,
    )
    return ok(
        TraceStatsResponse.model_validate(stats, from_attributes=True).model_dump(),
    )


@router.get("/ingestion-health")
async def ingestion_health(
    request: Request,
    module: ObservabilityModuleDep,
):
    queue_stats = None
    worker_tasks = {}
    queue = getattr(request.app.state, "queue_backend", None)
    if queue is not None:
        queue_stats = await queue.queue_stats(TRACE_QUEUE_NAME)
        worker_tasks = {
            "trace_ingestion": queue_stats,
            "document_indexing": await queue.queue_stats("document_processing"),
        }
    return ok(
        IngestionHealthResponse(
            publisher=module.ingestion_health(),
            queue=queue_stats,
            worker_tasks=worker_tasks,
        ).model_dump(),
    )


@router.get("/{trace_id}")
async def get_trace_detail(trace_id: str, store: TraceStoreDep):
    trace = await store.get_trace(trace_id)
    if trace is None:
        from common.errors import NotFoundError

        raise NotFoundError("Trace", trace_id)
    spans = await store.get_trace_spans(trace_id)
    return ok(
        TraceDetailResponse(
            trace=_to_trace_item(trace),
            spans=[_to_span_item(span) for span in spans],
        ).model_dump(),
    )
