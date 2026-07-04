"""Model-usage monitoring queries over model_request_logs.

Mirrors the read pattern of cost_analysis.CostAggregator: resolve the table
object via the session's bound metadata and run SQL aggregation / pagination.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from llm_gateway.usage.orm_models import ModelRequestLogOrm

from .schemas import (
    DistinctErrorCodesResponse,
    ErrorRecordViewResponse,
    ModelUsageSummaryResponse,
    MonitoringOverviewResponse,
    UsageRequestViewResponse,
)

_REQUEST_LOG_TABLE = "model_request_logs"


def _to_model_summary(row) -> ModelUsageSummaryResponse:
    return ModelUsageSummaryResponse(
        model_key=row.model_key,
        total_requests=row.total_requests,
        success_count=row.success_count,
        error_count=row.error_count,
        total_input_tokens=row.total_input_tokens,
        total_output_tokens=row.total_output_tokens,
        total_estimated_cost=float(row.total_estimated_cost),
        avg_duration_ms=round(float(row.avg_duration_ms), 1),
        total_cache_write_tokens=int(row.total_cache_write_tokens),
        total_cache_read_tokens=int(row.total_cache_read_tokens),
    )


class ModelUsageService:
    """Serves the model-monitoring UI from model_request_logs."""

    def __init__(self, session_factory) -> None:
        self._session_factory = session_factory

    @staticmethod
    def _tbl():
        return ModelRequestLogOrm.__table__

    @staticmethod
    def _filters(tbl, from_dt, to_dt, model_key):
        conds = []
        if from_dt is not None:
            conds.append(tbl.c.StartedAtUtc >= from_dt)
        if to_dt is not None:
            conds.append(tbl.c.StartedAtUtc < to_dt)
        if model_key:
            conds.append(tbl.c.ModelKey == model_key)
        return conds

    async def get_overview(
        self, *, from_dt, to_dt, model_key
    ) -> MonitoringOverviewResponse:
        """Return global totals + per-model summaries in one query.

        Replaces the old pattern where the frontend had to loop-paginate
        /statistics/models and compute globals client-side.
        """
        async with self._session_factory() as session:
            tbl = self._tbl()
            conds = self._filters(tbl, from_dt, to_dt, model_key)

            stmt = (
                select(
                    tbl.c.ModelKey.label("model_key"),
                    func.count().label("total_requests"),
                    func.count().filter(tbl.c.Success.is_(True)).label("success_count"),
                    func.count().filter(tbl.c.Success.is_(False)).label("error_count"),
                    func.coalesce(func.sum(tbl.c.TotalInputTokens), 0).label("total_input_tokens"),
                    func.coalesce(func.sum(tbl.c.TotalOutputTokens), 0).label("total_output_tokens"),
                    func.coalesce(func.sum(tbl.c.TotalEstimatedCost), 0).label("total_estimated_cost"),
                    func.coalesce(func.avg(tbl.c.TotalDurationMs), 0).label("avg_duration_ms"),
                    func.coalesce(func.sum(tbl.c.CacheWriteTokens), 0).label("total_cache_write_tokens"),
                    func.coalesce(func.sum(tbl.c.CacheReadTokens), 0).label("total_cache_read_tokens"),
                )
                .where(*conds)
                .group_by(tbl.c.ModelKey)
                .order_by(func.sum(tbl.c.TotalEstimatedCost).desc())
            )
            rows = (await session.execute(stmt)).all()
            summaries = [_to_model_summary(r) for r in rows]

            # Compute global totals from per-model summaries (cheap — few models)
            total_requests = sum(s.total_requests for s in summaries)
            total_tokens = sum(s.total_input_tokens + s.total_output_tokens for s in summaries)
            total_errors = sum(s.error_count for s in summaries)
            if total_requests > 0:
                avg_latency = sum(
                    s.avg_duration_ms * s.total_requests for s in summaries
                ) / total_requests
            else:
                avg_latency = 0.0

            return MonitoringOverviewResponse(
                total_requests=total_requests,
                total_tokens=total_tokens,
                total_errors=total_errors,
                average_latency_ms=round(avg_latency, 1),
                model_summaries=summaries,
            )

    async def get_distinct_error_codes(self) -> DistinctErrorCodesResponse:
        """Return the set of error codes that actually appear in the table."""
        async with self._session_factory() as session:
            tbl = self._tbl()
            stmt = (
                select(tbl.c.ErrorCode)
                .where(tbl.c.Success.is_(False), tbl.c.ErrorCode.isnot(None))
                .distinct()
                .order_by(tbl.c.ErrorCode)
            )
            rows = (await session.execute(stmt)).all()
            return DistinctErrorCodesResponse(
                error_codes=[r.ErrorCode for r in rows if r.ErrorCode]
            )

    async def list_model_summaries(
        self, *, from_dt, to_dt, model_key, page, page_size
    ) -> tuple[list[ModelUsageSummaryResponse], int]:
        async with self._session_factory() as session:
            tbl = self._tbl()
            conds = self._filters(tbl, from_dt, to_dt, model_key)

            base = select(tbl.c.ModelKey)
            if conds:
                base = base.where(*conds)
            count_stmt = select(func.count()).select_from(base.group_by(tbl.c.ModelKey).subquery())
            total = (await session.execute(count_stmt)).scalar_one()

            stmt = (
                select(
                    tbl.c.ModelKey.label("model_key"),
                    func.count().label("total_requests"),
                    func.count().filter(tbl.c.Success.is_(True)).label("success_count"),
                    func.count().filter(tbl.c.Success.is_(False)).label("error_count"),
                    func.coalesce(func.sum(tbl.c.TotalInputTokens), 0).label("total_input_tokens"),
                    func.coalesce(func.sum(tbl.c.TotalOutputTokens), 0).label("total_output_tokens"),
                    func.coalesce(func.sum(tbl.c.TotalEstimatedCost), 0).label("total_estimated_cost"),
                    func.coalesce(func.avg(tbl.c.TotalDurationMs), 0).label("avg_duration_ms"),
                    func.coalesce(func.sum(tbl.c.CacheWriteTokens), 0).label("total_cache_write_tokens"),
                    func.coalesce(func.sum(tbl.c.CacheReadTokens), 0).label("total_cache_read_tokens"),
                )
                .where(*conds)
                .group_by(tbl.c.ModelKey)
                .order_by(func.sum(tbl.c.TotalEstimatedCost).desc())
                .limit(page_size)
                .offset((page - 1) * page_size)
            )
            rows = (await session.execute(stmt)).all()
            items = [_to_model_summary(r) for r in rows]
            return items, total

    async def list_requests(
        self, *, from_dt, to_dt, model_key, page, page_size
    ) -> tuple[list[UsageRequestViewResponse], int]:
        async with self._session_factory() as session:
            tbl = self._tbl()
            conds = self._filters(tbl, from_dt, to_dt, model_key)

            total = (
                await session.execute(select(func.count()).select_from(tbl).where(*conds))
            ).scalar_one()

            stmt = (
                select(tbl)
                .where(*conds)
                .order_by(tbl.c.StartedAtUtc.desc())
                .limit(page_size)
                .offset((page - 1) * page_size)
            )
            rows = (await session.execute(stmt)).all()
            items = [
                UsageRequestViewResponse(
                    request_id=r.RequestId,
                    model_key=r.ModelKey,
                    capability=r.Capability,
                    success=r.Success,
                    attempt_count=r.AttemptCount,
                    final_instance_key=r.FinalInstanceKey,
                    error_code=r.ErrorCode,
                    error_message=r.ErrorMessage,
                    total_input_tokens=r.TotalInputTokens,
                    total_output_tokens=r.TotalOutputTokens,
                    total_estimated_cost=float(r.TotalEstimatedCost),
                    total_duration_ms=r.TotalDurationMs,
                    cache_write_tokens=r.CacheWriteTokens,
                    cache_read_tokens=r.CacheReadTokens,
                    started_at_utc=r.StartedAtUtc,
                    completed_at_utc=r.CompletedAtUtc,
                )
                for r in rows
            ]
            return items, total

    async def list_errors(
        self, *, from_dt, to_dt, model_key, error_code, page, page_size
    ) -> tuple[list[ErrorRecordViewResponse], int]:
        async with self._session_factory() as session:
            tbl = self._tbl()
            conds = self._filters(tbl, from_dt, to_dt, model_key)
            conds.append(tbl.c.Success.is_(False))
            if error_code:
                conds.append(tbl.c.ErrorCode == error_code)

            total = (
                await session.execute(select(func.count()).select_from(tbl).where(*conds))
            ).scalar_one()

            stmt = (
                select(tbl)
                .where(*conds)
                .order_by(tbl.c.StartedAtUtc.desc())
                .limit(page_size)
                .offset((page - 1) * page_size)
            )
            rows = (await session.execute(stmt)).all()
            items = [
                ErrorRecordViewResponse(
                    request_id=r.RequestId,
                    model_key=r.ModelKey,
                    instance_key=r.FinalInstanceKey,
                    capability=r.Capability,
                    error_code=r.ErrorCode,
                    error_message=r.ErrorMessage,
                    duration_ms=r.TotalDurationMs,
                    started_at_utc=r.StartedAtUtc,
                    completed_at_utc=r.CompletedAtUtc,
                )
                for r in rows
            ]
            return items, total
