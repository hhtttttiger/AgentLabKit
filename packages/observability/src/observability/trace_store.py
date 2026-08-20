from __future__ import annotations

import base64
import json
from datetime import datetime, timedelta, timezone
from typing import Protocol, runtime_checkable

from sqlalchemy import text as sa_text

from .contracts import SpanEnvelope, TraceEnvelope, TracePage, TraceRecord, TraceStats


@runtime_checkable
class TraceStore(Protocol):
    async def ingest_trace(self, envelope: TraceEnvelope) -> None: ...
    async def get_trace(self, trace_id: str) -> TraceRecord | None: ...
    async def get_trace_spans(self, trace_id: str) -> list[SpanEnvelope]: ...
    async def list_traces(
        self,
        *,
        agent_key: str | None = None,
        session_id: str | None = None,
        status: str | None = None,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        cursor: str | None = None,
        limit: int = 20,
    ) -> TracePage: ...
    async def get_stats(
        self,
        *,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
    ) -> TraceStats: ...
    async def delete_expired(self, *, retention_days: int, batch_size: int) -> int: ...


class PostgresTraceStore:
    def __init__(self, session_factory) -> None:
        self._session_factory = session_factory

    async def ingest_trace(self, envelope: TraceEnvelope) -> None:
        trace_params = {
            "trace_id": envelope.trace_id,
            "root_span_id": envelope.root_span_id,
            "run_id": envelope.run_id,
            "agent_key": envelope.agent_key,
            "session_id": envelope.session_id,
            "user_id": envelope.user_id,
            "correlation_id": envelope.correlation_id,
            "status": envelope.status,
            "duration": envelope.total_duration_ms,
            "input_tokens": envelope.total_input_tokens,
            "output_tokens": envelope.total_output_tokens,
            "cache_write": envelope.cache_write_tokens,
            "cache_read": envelope.cache_read_tokens,
            "cost": envelope.total_estimated_cost,
            "span_count": envelope.span_count,
            "dropped_count": envelope.dropped_span_count,
            "sample_reason": envelope.sample_reason,
            "attributes": json.dumps(envelope.attributes, ensure_ascii=False, default=str),
            "schema_version": envelope.schema_version,
            "started": envelope.started_at_utc,
            "completed": envelope.completed_at_utc,
        }
        span_params = [
            {
                "span_id": span.span_id,
                "trace_id": span.trace_id,
                "parent_span_id": span.parent_span_id,
                "name": span.name,
                "kind": span.kind,
                "status": span.status,
                "scope": span.instrumentation_scope,
                "started": span.started_at_utc,
                "completed": span.completed_at_utc,
                "duration": span.duration_ms,
                "attributes": json.dumps(span.attributes, ensure_ascii=False, default=str),
                "events": json.dumps(span.events, ensure_ascii=False, default=str),
                "links": json.dumps(span.links, ensure_ascii=False, default=str),
                "error_code": span.error_code,
                "error_message": span.error_message,
            }
            for span in envelope.spans
        ]
        async with self._session_factory() as session:
            await session.execute(
                sa_text(
                    """
                    INSERT INTO trace_records (
                        trace_id, root_span_id, run_id, agent_key, session_id, user_id,
                        correlation_id, status, total_duration_ms, total_input_tokens,
                        total_output_tokens, cache_write_tokens, cache_read_tokens,
                        total_estimated_cost, span_count, dropped_span_count, sample_reason,
                        attributes_json, schema_version, started_at_utc, completed_at_utc,
                        created_at_utc, updated_at_utc
                    ) VALUES (
                        :trace_id, :root_span_id, CAST(:run_id AS uuid), :agent_key, :session_id,
                        :user_id, :correlation_id, :status, :duration, :input_tokens,
                        :output_tokens, :cache_write, :cache_read, :cost, :span_count,
                        :dropped_count, :sample_reason, CAST(:attributes AS jsonb),
                        :schema_version, :started, :completed, NOW(), NOW()
                    )
                    ON CONFLICT (trace_id) DO UPDATE SET
                        root_span_id=EXCLUDED.root_span_id, run_id=EXCLUDED.run_id,
                        agent_key=EXCLUDED.agent_key, session_id=EXCLUDED.session_id,
                        user_id=EXCLUDED.user_id, correlation_id=EXCLUDED.correlation_id,
                        status=EXCLUDED.status, total_duration_ms=EXCLUDED.total_duration_ms,
                        total_input_tokens=EXCLUDED.total_input_tokens,
                        total_output_tokens=EXCLUDED.total_output_tokens,
                        cache_write_tokens=EXCLUDED.cache_write_tokens,
                        cache_read_tokens=EXCLUDED.cache_read_tokens,
                        total_estimated_cost=EXCLUDED.total_estimated_cost,
                        span_count=EXCLUDED.span_count,
                        dropped_span_count=EXCLUDED.dropped_span_count,
                        sample_reason=EXCLUDED.sample_reason,
                        attributes_json=EXCLUDED.attributes_json,
                        schema_version=EXCLUDED.schema_version,
                        started_at_utc=EXCLUDED.started_at_utc,
                        completed_at_utc=EXCLUDED.completed_at_utc,
                        updated_at_utc=NOW()
                    """,
                ),
                trace_params,
            )
            if span_params:
                await session.execute(
                    sa_text(
                        """
                        INSERT INTO trace_spans (
                            span_id, trace_id, parent_span_id, name, span_kind, status,
                            instrumentation_scope, started_at_utc, completed_at_utc,
                            duration_ms, attributes_json, events_json, links_json,
                            error_code, error_message, created_at_utc, updated_at_utc
                        ) VALUES (
                            :span_id, :trace_id, :parent_span_id, :name, :kind, :status,
                            :scope, :started, :completed, :duration,
                            CAST(:attributes AS jsonb), CAST(:events AS jsonb),
                            CAST(:links AS jsonb), :error_code, :error_message, NOW(), NOW()
                        )
                        ON CONFLICT (span_id) DO UPDATE SET
                            parent_span_id=EXCLUDED.parent_span_id, name=EXCLUDED.name,
                            span_kind=EXCLUDED.span_kind, status=EXCLUDED.status,
                            instrumentation_scope=EXCLUDED.instrumentation_scope,
                            started_at_utc=EXCLUDED.started_at_utc,
                            completed_at_utc=EXCLUDED.completed_at_utc,
                            duration_ms=EXCLUDED.duration_ms,
                            attributes_json=EXCLUDED.attributes_json,
                            events_json=EXCLUDED.events_json, links_json=EXCLUDED.links_json,
                            error_code=EXCLUDED.error_code, error_message=EXCLUDED.error_message,
                            updated_at_utc=NOW()
                        """,
                    ),
                    span_params,
                )
            await session.commit()

    async def get_trace(self, trace_id: str) -> TraceRecord | None:
        async with self._session_factory() as session:
            result = await session.execute(
                sa_text(f"{_TRACE_SELECT} WHERE trace_id=:trace_id"),
                {"trace_id": trace_id},
            )
            row = result.mappings().first()
            return _trace_from_row(row) if row else None

    async def get_trace_spans(self, trace_id: str) -> list[SpanEnvelope]:
        async with self._session_factory() as session:
            result = await session.execute(
                sa_text(
                    """
                    SELECT span_id, trace_id, parent_span_id, name, span_kind, status,
                           instrumentation_scope, started_at_utc, completed_at_utc,
                           duration_ms, attributes_json, events_json, links_json,
                           error_code, error_message
                    FROM trace_spans WHERE trace_id=:trace_id
                    ORDER BY started_at_utc, span_id
                    """,
                ),
                {"trace_id": trace_id},
            )
            return [_span_from_row(row) for row in result.mappings().all()]

    async def list_traces(
        self,
        *,
        agent_key: str | None = None,
        session_id: str | None = None,
        status: str | None = None,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        cursor: str | None = None,
        limit: int = 20,
    ) -> TracePage:
        conditions: list[str] = []
        params: dict[str, object] = {"limit": limit + 1}
        for value, expression, key in (
            (agent_key, "agent_key=:agent_key", "agent_key"),
            (session_id, "session_id=:session_id", "session_id"),
            (status, "status=:status", "status"),
            (from_date, "started_at_utc>=:from_date", "from_date"),
            (to_date, "started_at_utc<:to_date", "to_date"),
        ):
            if value is not None:
                conditions.append(expression)
                params[key] = value
        if cursor:
            cursor_time, cursor_id = decode_cursor(cursor)
            conditions.append("(started_at_utc, trace_id) < (:cursor_time, :cursor_id)")
            params.update({"cursor_time": cursor_time, "cursor_id": cursor_id})
        where = f" WHERE {' AND '.join(conditions)}" if conditions else ""

        async with self._session_factory() as session:
            result = await session.execute(
                sa_text(
                    f"{_TRACE_SELECT}{where} "
                    "ORDER BY started_at_utc DESC, trace_id DESC LIMIT :limit",
                ),
                params,
            )
            records = [_trace_from_row(row) for row in result.mappings().all()]
        has_more = len(records) > limit
        items = records[:limit]
        next_cursor = (
            encode_cursor(items[-1].started_at_utc, items[-1].trace_id)
            if has_more and items
            else None
        )
        return TracePage(items=items, next_cursor=next_cursor)

    async def get_stats(
        self,
        *,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
    ) -> TraceStats:
        conditions: list[str] = []
        params: dict[str, object] = {}
        if from_date:
            conditions.append("started_at_utc>=:from_date")
            params["from_date"] = from_date
        if to_date:
            conditions.append("started_at_utc<:to_date")
            params["to_date"] = to_date
        where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
        async with self._session_factory() as session:
            row = (
                await session.execute(
                    sa_text(
                        """
                        SELECT COUNT(*) AS total_traces,
                               COUNT(*) FILTER (WHERE status='error') AS error_count,
                               COUNT(*) FILTER (WHERE status='timeout') AS timeout_count,
                               COUNT(*) FILTER (WHERE status='cancelled') AS cancelled_count,
                               COALESCE(percentile_cont(0.5) WITHIN GROUP
                                   (ORDER BY total_duration_ms), 0) AS p50_duration_ms,
                               COALESCE(percentile_cont(0.95) WITHIN GROUP
                                   (ORDER BY total_duration_ms), 0) AS p95_duration_ms,
                               COALESCE(SUM(total_input_tokens + total_output_tokens), 0) AS total_tokens,
                               COALESCE(SUM(total_estimated_cost), 0) AS total_estimated_cost
                        FROM trace_records
                        """
                        + where,
                    ),
                    params,
                )
            ).mappings().first()
        return TraceStats.model_validate(dict(row or {}))

    async def delete_expired(self, *, retention_days: int, batch_size: int) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
        async with self._session_factory() as session:
            result = await session.execute(
                sa_text(
                    """
                    DELETE FROM trace_records WHERE id IN (
                        SELECT id FROM trace_records
                        WHERE completed_at_utc < :cutoff
                        ORDER BY completed_at_utc
                        LIMIT :batch_size
                    )
                    """,
                ),
                {"cutoff": cutoff, "batch_size": batch_size},
            )
            await session.commit()
            return int(result.rowcount or 0)


_TRACE_SELECT = """
SELECT trace_id, root_span_id, run_id::text AS run_id, agent_key, session_id,
       user_id, correlation_id, status, total_duration_ms, total_input_tokens,
       total_output_tokens, cache_write_tokens, cache_read_tokens,
       total_estimated_cost, span_count, dropped_span_count, sample_reason,
       attributes_json, schema_version, started_at_utc, completed_at_utc
FROM trace_records
"""


def encode_cursor(started_at: datetime, trace_id: str) -> str:
    raw = json.dumps([started_at.isoformat(), trace_id], separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def decode_cursor(cursor: str) -> tuple[datetime, str]:
    padding = "=" * (-len(cursor) % 4)
    started, trace_id = json.loads(base64.urlsafe_b64decode(cursor + padding))
    return datetime.fromisoformat(started), str(trace_id)


def _trace_from_row(row) -> TraceRecord:
    values = dict(row)
    values["attributes"] = values.pop("attributes_json") or {}
    return TraceRecord.model_validate(values)


def _span_from_row(row) -> SpanEnvelope:
    values = dict(row)
    values["kind"] = values.pop("span_kind")
    values["attributes"] = values.pop("attributes_json") or {}
    values["events"] = values.pop("events_json") or []
    values["links"] = values.pop("links_json") or []
    return SpanEnvelope.model_validate(values)


__all__ = [
    "PostgresTraceStore",
    "TraceStore",
    "decode_cursor",
    "encode_cursor",
]
