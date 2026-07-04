"""TraceStore — Protocol + PostgresTraceStore。

使用原始 SQL（text query）操作 trace_records / trace_spans 表，
避免与 backend ORM 强耦合。
"""

from __future__ import annotations

import logging
from typing import Protocol, runtime_checkable

from .contracts import TraceRecord, SpanRecord

logger = logging.getLogger(__name__)


# ── Column name constants ──────────────────────────────────────────────
# Single source of truth for trace_records / trace_spans column names.
# Used by PostgresTraceStore to avoid hardcoded strings in raw SQL.


class _TC:
    """trace_records column names."""
    trace_id = "trace_id"
    root_span_id = "root_span_id"
    agent_key = "agent_key"
    session_id = "session_id"
    status = "status"
    total_duration_ms = "total_duration_ms"
    total_input_tokens = "total_input_tokens"
    total_output_tokens = "total_output_tokens"
    total_estimated_cost = "total_estimated_cost"
    span_count = "span_count"
    started_at_utc = "started_at_utc"
    completed_at_utc = "completed_at_utc"


class _SC:
    """trace_spans column names."""
    trace_id = "trace_id"
    span_id = "span_id"
    parent_span_id = "parent_span_id"
    span_kind = "span_kind"
    name = "name"
    status = "status"
    started_at_utc = "started_at_utc"
    completed_at_utc = "completed_at_utc"
    duration_ms = "duration_ms"
    attributes_json = "attributes_json"
    error_code = "error_code"
    error_message = "error_message"


@runtime_checkable
class TraceStore(Protocol):
    async def save_trace(self, trace: TraceRecord) -> None: ...
    async def save_spans(self, spans: list[SpanRecord]) -> None: ...
    async def save_trace_and_spans(self, trace: TraceRecord, spans: list[SpanRecord]) -> None: ...
    async def get_trace(self, trace_id: str) -> TraceRecord | None: ...
    async def get_trace_spans(self, trace_id: str) -> list[SpanRecord]: ...
    async def list_traces(
        self,
        *,
        agent_key: str | None = None,
        status: str | None = None,
        from_date=None,
        to_date=None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[TraceRecord], int]: ...
    async def get_stats(
        self,
        *,
        from_date=None,
        to_date=None,
    ) -> dict: ...


class PostgresTraceStore:
    """基于 PostgreSQL 的 TraceStore 实现。"""

    def __init__(self, session_factory) -> None:
        self._session_factory = session_factory

    async def save_trace(self, trace: TraceRecord) -> None:
        from sqlalchemy import text as sa_text

        logger.info("save_trace: trace_id=%s span_count=%d", trace.trace_id, trace.span_count)
        async with self._session_factory() as session:
            await session.execute(
                sa_text(
                    "INSERT INTO trace_records "
                    "(trace_id, root_span_id, agent_key, session_id, status, "
                    " total_duration_ms, total_input_tokens, total_output_tokens, "
                    " total_estimated_cost, span_count, started_at_utc, completed_at_utc, "
                    " created_at_utc, updated_at_utc) "
                    "VALUES (:tid, :root, :agent, :sess, :status, "
                    " :dur, :in_tok, :out_tok, :cost, :cnt, :start, :end, NOW(), NOW()) "
                    "ON CONFLICT (trace_id) DO UPDATE SET "
                    " status = EXCLUDED.status, "
                    " total_duration_ms = EXCLUDED.total_duration_ms, "
                    " total_input_tokens = EXCLUDED.total_input_tokens, "
                    " total_output_tokens = EXCLUDED.total_output_tokens, "
                    " total_estimated_cost = EXCLUDED.total_estimated_cost, "
                    " span_count = EXCLUDED.span_count, "
                    " completed_at_utc = EXCLUDED.completed_at_utc, "
                    " updated_at_utc = NOW()"
                ),
                {
                    "tid": trace.trace_id,
                    "root": trace.root_span_id,
                    "agent": trace.agent_key,
                    "sess": trace.session_id,
                    "status": trace.status,
                    "dur": trace.total_duration_ms,
                    "in_tok": trace.total_input_tokens,
                    "out_tok": trace.total_output_tokens,
                    "cost": trace.total_estimated_cost,
                    "cnt": trace.span_count,
                    "start": trace.started_at_utc,
                    "end": trace.completed_at_utc,
                },
            )
            await session.commit()

    async def save_spans(self, spans: list[SpanRecord]) -> None:
        if not spans:
            logger.warning("save_spans: called with empty spans list, skipping")
            return
        from sqlalchemy import text as sa_text
        import json

        trace_id = spans[0].trace_id
        logger.info("save_spans: saving %d spans for trace_id=%s", len(spans), trace_id)
        try:
            # Build a single multi-VALUES INSERT for all spans
            value_clauses: list[str] = []
            params: dict[str, object] = {}
            for i, span in enumerate(spans):
                value_clauses.append(
                    f"(:tid_{i}, :sid_{i}, :pid_{i}, :kind_{i}, :name_{i}, :status_{i}, "
                    f" :start_{i}, :end_{i}, :dur_{i}, CAST(:attrs_{i} AS jsonb), "
                    f" :ecode_{i}, :emsg_{i}, NOW(), NOW())"
                )
                params.update({
                    f"tid_{i}": span.trace_id,
                    f"sid_{i}": span.span_id,
                    f"pid_{i}": span.parent_span_id,
                    f"kind_{i}": span.span_kind,
                    f"name_{i}": span.name,
                    f"status_{i}": span.status,
                    f"start_{i}": span.started_at_utc,
                    f"end_{i}": span.completed_at_utc,
                    f"dur_{i}": span.duration_ms,
                    f"attrs_{i}": json.dumps(span.attributes),
                    f"ecode_{i}": span.error_code,
                    f"emsg_{i}": span.error_message,
                })

            sql = (
                "INSERT INTO trace_spans "
                "(trace_id, span_id, parent_span_id, span_kind, name, status, "
                " started_at_utc, completed_at_utc, duration_ms, "
                " attributes_json, error_code, error_message, "
                " created_at_utc, updated_at_utc) "
                f"VALUES {', '.join(value_clauses)} "
                "ON CONFLICT (span_id) DO NOTHING"
            )

            async with self._session_factory() as session:
                await session.execute(sa_text(sql), params)
                await session.commit()
                logger.info("save_spans: successfully committed %d spans", len(spans))
        except Exception:
            logger.exception("save_spans: failed to save %d spans", len(spans))
            raise

    async def save_trace_and_spans(self, trace: TraceRecord, spans: list[SpanRecord]) -> None:
        """Atomically save a trace and its spans in a single transaction."""
        from sqlalchemy import text as sa_text
        import json

        logger.info(
            "save_trace_and_spans: trace_id=%s span_count=%d spans_len=%d",
            trace.trace_id, trace.span_count, len(spans),
        )
        try:
            async with self._session_factory() as session:
                # Save trace
                await session.execute(
                    sa_text(
                        "INSERT INTO trace_records "
                        "(trace_id, root_span_id, agent_key, session_id, status, "
                        " total_duration_ms, total_input_tokens, total_output_tokens, "
                        " total_estimated_cost, span_count, started_at_utc, completed_at_utc, "
                        " created_at_utc, updated_at_utc) "
                        "VALUES (:tid, :root, :agent, :sess, :status, "
                        " :dur, :in_tok, :out_tok, :cost, :cnt, :start, :end, NOW(), NOW()) "
                        "ON CONFLICT (trace_id) DO UPDATE SET "
                        " status = EXCLUDED.status, "
                        " total_duration_ms = EXCLUDED.total_duration_ms, "
                        " total_input_tokens = EXCLUDED.total_input_tokens, "
                        " total_output_tokens = EXCLUDED.total_output_tokens, "
                        " total_estimated_cost = EXCLUDED.total_estimated_cost, "
                        " span_count = EXCLUDED.span_count, "
                        " completed_at_utc = EXCLUDED.completed_at_utc, "
                        " updated_at_utc = NOW()"
                    ),
                    {
                        "tid": trace.trace_id,
                        "root": trace.root_span_id,
                        "agent": trace.agent_key,
                        "sess": trace.session_id,
                        "status": trace.status,
                        "dur": trace.total_duration_ms,
                        "in_tok": trace.total_input_tokens,
                        "out_tok": trace.total_output_tokens,
                        "cost": trace.total_estimated_cost,
                        "cnt": trace.span_count,
                        "start": trace.started_at_utc,
                        "end": trace.completed_at_utc,
                    },
                )

                # Save spans (batch INSERT)
                if spans:
                    value_clauses: list[str] = []
                    span_params: dict[str, object] = {}
                    for i, span in enumerate(spans):
                        value_clauses.append(
                            f"(:tid_{i}, :sid_{i}, :pid_{i}, :kind_{i}, :name_{i}, :status_{i}, "
                            f" :start_{i}, :end_{i}, :dur_{i}, CAST(:attrs_{i} AS jsonb), "
                            f" :ecode_{i}, :emsg_{i}, NOW(), NOW())"
                        )
                        span_params.update({
                            f"tid_{i}": span.trace_id,
                            f"sid_{i}": span.span_id,
                            f"pid_{i}": span.parent_span_id,
                            f"kind_{i}": span.span_kind,
                            f"name_{i}": span.name,
                            f"status_{i}": span.status,
                            f"start_{i}": span.started_at_utc,
                            f"end_{i}": span.completed_at_utc,
                            f"dur_{i}": span.duration_ms,
                            f"attrs_{i}": json.dumps(span.attributes),
                            f"ecode_{i}": span.error_code,
                            f"emsg_{i}": span.error_message,
                        })

                    span_sql = (
                        "INSERT INTO trace_spans "
                        "(trace_id, span_id, parent_span_id, span_kind, name, status, "
                        " started_at_utc, completed_at_utc, duration_ms, "
                        " attributes_json, error_code, error_message, "
                        " created_at_utc, updated_at_utc) "
                        f"VALUES {', '.join(value_clauses)} "
                        "ON CONFLICT (span_id) DO NOTHING"
                    )
                    await session.execute(sa_text(span_sql), span_params)

                await session.commit()
                logger.info(
                    "save_trace_and_spans: committed trace_id=%s with %d spans",
                    trace.trace_id, len(spans),
                )
        except Exception:
            logger.exception(
                "save_trace_and_spans: failed for trace_id=%s", trace.trace_id,
            )
            raise

    async def get_trace(self, trace_id: str) -> TraceRecord | None:
        from sqlalchemy import text as sa_text

        async with self._session_factory() as session:
            result = await session.execute(
                sa_text(
                    "SELECT trace_id, root_span_id, agent_key, session_id, status, "
                    " total_duration_ms, total_input_tokens, total_output_tokens, "
                    " total_estimated_cost, span_count, started_at_utc, completed_at_utc "
                    "FROM trace_records WHERE trace_id = :tid"
                ),
                {"tid": trace_id},
            )
            row = result.mappings().first()
            if not row:
                return None
            return TraceRecord(**dict(row))

    async def get_trace_spans(self, trace_id: str) -> list[SpanRecord]:
        from sqlalchemy import text as sa_text
        import json

        async with self._session_factory() as session:
            result = await session.execute(
                sa_text(
                    "SELECT span_id, trace_id, parent_span_id, span_kind, name, status, "
                    " started_at_utc, completed_at_utc, duration_ms, "
                    " attributes_json, error_code, error_message "
                    "FROM trace_spans WHERE trace_id = :tid "
                    "ORDER BY started_at_utc"
                ),
                {"tid": trace_id},
            )
            rows = result.mappings().all()
            logger.info("get_trace_spans: trace_id=%s found %d rows", trace_id, len(rows))
            spans = []
            for row in rows:
                d = dict(row)
                attrs_raw = d.pop("attributes_json", None)
                d["attributes"] = json.loads(attrs_raw) if isinstance(attrs_raw, str) else (attrs_raw or {})
                spans.append(SpanRecord(**d))
            return spans

    async def list_traces(
        self,
        *,
        agent_key: str | None = None,
        status: str | None = None,
        from_date=None,
        to_date=None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[TraceRecord], int]:
        from sqlalchemy import text as sa_text

        conditions: list[str] = []
        params: dict[str, object] = {"lim": page_size, "offset": (page - 1) * page_size}
        if agent_key:
            conditions.append(f"{_TC.agent_key} = :agent")
            params["agent"] = agent_key
        if status:
            conditions.append(f"{_TC.status} = :status")
            params["status"] = status
        if from_date:
            conditions.append(f"{_TC.started_at_utc} >= :from")
            params["from"] = from_date
        if to_date:
            conditions.append(f"{_TC.started_at_utc} < :to")
            params["to"] = to_date

        where = (" WHERE " + " AND ".join(conditions)) if conditions else ""

        async with self._session_factory() as session:
            count_result = await session.execute(
                sa_text(f"SELECT COUNT(*) FROM trace_records{where}"), params,
            )
            total = int(count_result.scalar_one())

            cols = (
                f"{_TC.trace_id}, {_TC.root_span_id}, {_TC.agent_key}, "
                f"{_TC.session_id}, {_TC.status}, "
                f"{_TC.total_duration_ms}, {_TC.total_input_tokens}, {_TC.total_output_tokens}, "
                f"{_TC.total_estimated_cost}, {_TC.span_count}, "
                f"{_TC.started_at_utc}, {_TC.completed_at_utc}"
            )
            result = await session.execute(
                sa_text(
                    f"SELECT {cols} "
                    f"FROM trace_records{where} "
                    f"ORDER BY {_TC.started_at_utc} DESC "
                    f"LIMIT :lim OFFSET :offset"
                ),
                params,
            )
            traces = [TraceRecord(**dict(row)) for row in result.mappings().all()]
            return traces, total

    async def get_stats(
        self,
        *,
        from_date=None,
        to_date=None,
    ) -> dict:
        from sqlalchemy import text as sa_text

        conditions: list[str] = []
        params: dict[str, object] = {}
        if from_date:
            conditions.append(f"{_TC.started_at_utc} >= :from")
            params["from"] = from_date
        if to_date:
            conditions.append(f"{_TC.started_at_utc} < :to")
            params["to"] = to_date

        where = (" WHERE " + " AND ".join(conditions)) if conditions else ""

        async with self._session_factory() as session:
            result = await session.execute(
                sa_text(
                    f"SELECT COUNT(*) as total_traces, "
                    f" COALESCE(AVG({_TC.total_duration_ms}), 0) as avg_duration_ms, "
                    f" COALESCE(SUM({_TC.total_input_tokens} + {_TC.total_output_tokens}), 0) as total_tokens, "
                    f" COALESCE(SUM(CASE WHEN {_TC.status}='error' THEN 1 ELSE 0 END), 0) as error_count "
                    f"FROM trace_records{where}"
                ),
                params,
            )
            row = result.mappings().first()
            return dict(row) if row else {}
