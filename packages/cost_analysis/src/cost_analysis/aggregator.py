"""成本聚合器 — 对现有 usage 表做 GROUP BY 查询。

仅读取 ``model_request_logs`` 表（来自 llm_gateway.usage.orm_models），
不修改任何现有数据。
"""

from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import BigInteger, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = logging.getLogger(__name__)

from llm_gateway.usage.orm_models import ModelRequestLogOrm

from .contracts import CostBreakdown, CostTrendPoint, CostOverview, Granularity

# ---------------------------------------------------------------------------
# 复用 llm_gateway 的 ORM 而非本地重复定义。
# 为了避免在包级别硬依赖 llm_gateway，这里用字符串引用表名，
# 在方法内通过 session 绑定自动解析。
# ---------------------------------------------------------------------------

_REQUEST_LOG_TABLE = "model_request_logs"


class CostAggregator:
    """SQL 聚合查询：按模型 / Agent / 时间维度汇总 cost / tokens / latency。"""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        # session_factory 是 async_sessionmaker 实例
        self._session_factory = session_factory

    # ── helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _tbl(session: AsyncSession):
        """通过 ORM ``__table__`` 拿到 Table 对象（AsyncEngine 无 metadata 属性）。"""
        return ModelRequestLogOrm.__table__

    # ── 总览 ───────────────────────────────────────────────────────────

    async def get_overview(
        self,
        *,
        from_date: datetime,
        to_date: datetime,
    ) -> CostOverview:
        """获取指定时间窗口内的成本概览。"""
        tbl = None
        async with self._session_factory() as session:
            tbl = self._tbl(session)

            # 当期汇总
            stmt = select(
                func.coalesce(func.sum(tbl.c.TotalEstimatedCost), 0).label("total_spend"),
                func.count().label("total_requests"),
                func.coalesce(func.sum(tbl.c.TotalInputTokens + tbl.c.TotalOutputTokens), 0).label("total_tokens"),
                func.coalesce(func.avg(tbl.c.TotalDurationMs), 0).label("avg_latency"),
                func.coalesce(func.sum(tbl.c.CacheWriteTokens), 0).label("cache_writes"),
                func.coalesce(func.sum(tbl.c.CacheReadTokens), 0).label("cache_reads"),
            ).where(
                tbl.c.StartedAtUtc >= from_date,
                tbl.c.StartedAtUtc < to_date,
            )

            result = await session.execute(stmt)
            row = result.one()

            # 上一周期（等长时间段）
            delta = to_date - from_date
            prev_from = from_date - delta
            prev_to = from_date

            stmt_prev = select(
                func.coalesce(func.sum(tbl.c.TotalEstimatedCost), 0).label("prev_spend"),
                func.count().label("prev_requests"),
            ).where(
                tbl.c.StartedAtUtc >= prev_from,
                tbl.c.StartedAtUtc < prev_to,
            )
            prev_result = await session.execute(stmt_prev)
            prev_row = prev_result.one()

            prev_spend = float(prev_row.prev_spend)
            prev_requests = int(prev_row.prev_requests)
            total_spend = float(row.total_spend)

            spend_change = (
                ((total_spend - prev_spend) / prev_spend * 100)
                if prev_spend > 0
                else 0.0
            )

            # Top 5 模型
            top_models = await self._breakdown(session, tbl, "ModelKey", from_date, to_date, limit=5)

            return CostOverview(
                total_spend=total_spend,
                total_requests=int(row.total_requests),
                total_tokens=int(row.total_tokens),
                avg_latency_ms=round(float(row.avg_latency), 1),
                period_start=from_date,
                period_end=to_date,
                prev_total_spend=prev_spend,
                prev_total_requests=prev_requests,
                spend_change_pct=round(spend_change, 1),
                top_models=top_models,
                total_cache_write_tokens=int(row.cache_writes),
                total_cache_read_tokens=int(row.cache_reads),
            )

    # ── 按维度分组 ─────────────────────────────────────────────────────

    async def get_breakdown_by_model(
        self,
        *,
        from_date: datetime,
        to_date: datetime,
        limit: int = 20,
    ) -> list[CostBreakdown]:
        async with self._session_factory() as session:
            tbl = self._tbl(session)
            return await self._breakdown(session, tbl, "ModelKey", from_date, to_date, limit)

    async def get_breakdown_by_capability(
        self,
        *,
        from_date: datetime,
        to_date: datetime,
        limit: int = 20,
    ) -> list[CostBreakdown]:
        async with self._session_factory() as session:
            tbl = self._tbl(session)
            return await self._breakdown(session, tbl, "Capability", from_date, to_date, limit)

    # ── 时间趋势 ───────────────────────────────────────────────────────

    async def get_cost_trend(
        self,
        *,
        granularity: Granularity,
        from_date: datetime,
        to_date: datetime,
    ) -> list[CostTrendPoint]:
        """按日 / 周 / 月聚合成本趋势。"""
        trunc_map = {
            Granularity.DAY: "day",
            Granularity.WEEK: "week",
            Granularity.MONTH: "month",
        }
        date_trunc = trunc_map[granularity]

        async with self._session_factory() as session:
            tbl = self._tbl(session)

            stmt = select(
                func.date_trunc(date_trunc, tbl.c.StartedAtUtc).label("period"),
                func.coalesce(func.sum(tbl.c.TotalEstimatedCost), 0).label("total_cost"),
                func.coalesce(func.sum(tbl.c.TotalInputTokens + tbl.c.TotalOutputTokens), 0).label("total_tokens"),
                func.count().label("request_count"),
                func.coalesce(func.sum(tbl.c.CacheWriteTokens), 0).label("cache_writes"),
                func.coalesce(func.sum(tbl.c.CacheReadTokens), 0).label("cache_reads"),
            ).where(
                tbl.c.StartedAtUtc >= from_date,
                tbl.c.StartedAtUtc < to_date,
            ).group_by(
                text("period"),
            ).order_by(
                text("period"),
            )

            result = await session.execute(stmt)
            return [
                CostTrendPoint(
                    period=row.period.isoformat() if row.period else "",
                    total_cost=float(row.total_cost),
                    total_tokens=int(row.total_tokens),
                    request_count=int(row.request_count),
                    total_cache_write_tokens=int(row.cache_writes),
                    total_cache_read_tokens=int(row.cache_reads),
                )
                for row in result.all()
            ]

    # ── 总花费 ─────────────────────────────────────────────────────────

    async def get_total_spend(
        self,
        *,
        from_date: datetime,
        to_date: datetime,
        scope_key: str | None = None,
    ) -> float:
        async with self._session_factory() as session:
            tbl = self._tbl(session)
            stmt = select(
                func.coalesce(func.sum(tbl.c.TotalEstimatedCost), 0),
            ).where(
                tbl.c.StartedAtUtc >= from_date,
                tbl.c.StartedAtUtc < to_date,
            )
            if scope_key:
                stmt = stmt.where(tbl.c.ModelKey == scope_key)
            result = await session.execute(stmt)
            return float(result.scalar_one())

    # ── 内部 ────────────────────────────────────────────────────────────

    @staticmethod
    async def _breakdown(
        session: AsyncSession,
        tbl,
        group_col: str,
        from_date: datetime,
        to_date: datetime,
        limit: int,
    ) -> list[CostBreakdown]:
        col = tbl.c[group_col]
        stmt = select(
            col.label("scope"),
            func.count().label("req_count"),
            func.coalesce(func.sum(tbl.c.TotalInputTokens), 0).label("in_tok"),
            func.coalesce(func.sum(tbl.c.TotalOutputTokens), 0).label("out_tok"),
            func.coalesce(func.sum(tbl.c.TotalEstimatedCost), 0).label("cost"),
            func.coalesce(func.avg(tbl.c.TotalDurationMs), 0).label("avg_lat"),
            func.coalesce(func.sum(tbl.c.CacheWriteTokens), 0).label("cache_writes"),
            func.coalesce(func.sum(tbl.c.CacheReadTokens), 0).label("cache_reads"),
        ).where(
            tbl.c.StartedAtUtc >= from_date,
            tbl.c.StartedAtUtc < to_date,
        ).group_by(
            col,
        ).order_by(
            text("cost DESC"),
        ).limit(limit)

        result = await session.execute(stmt)
        return [
            CostBreakdown(
                scope=row.scope,
                total_requests=int(row.req_count),
                total_input_tokens=int(row.in_tok),
                total_output_tokens=int(row.out_tok),
                total_estimated_cost=float(row.cost),
                avg_latency_ms=round(float(row.avg_lat), 1),
                total_cache_write_tokens=int(row.cache_writes),
                total_cache_read_tokens=int(row.cache_reads),
            )
            for row in result.all()
        ]
