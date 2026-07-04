"""预算管理 — 配额检查、告警评估。"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from alkit_db.snowflake import next_id as _next_snowflake_id
from .contracts import BudgetScopeType, BudgetStatus, CostAlertInfo

logger = logging.getLogger(__name__)


def _safe_scope_type(raw: str) -> BudgetScopeType:
    """将原始 scope_type 字符串转换为枚举，未知值回退为 GLOBAL。"""
    try:
        return BudgetScopeType(raw)
    except ValueError:
        logger.warning("Unknown BudgetScopeType=%r, falling back to GLOBAL", raw)
        return BudgetScopeType.GLOBAL


class BudgetManager:
    """预算配额检查与告警管理。

    读取 ``cost_budgets`` / ``cost_alerts`` 表（由 backend 模块定义 ORM）。
    为避免包级硬依赖，通过 Protocol / duck typing 使用 session。
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    # ── 预算状态查询 ────────────────────────────────────────────────────

    async def check_budget(
        self,
        session: AsyncSession,
        *,
        scope_type: BudgetScopeType,
        scope_key: str,
        current_spend: float,
    ) -> BudgetStatus | None:
        """查询某个 scope 下的预算状态。无预算返回 None。

        保留供外部调用方（如 llm_gateway）在事务上下文中使用。
        """
        # NOTE: 接受 AsyncSession 参数（非 session_factory）以支持调用方
        # 在现有事务上下文中复用 session。
        # ORM 类由 backend 模块定义，这里用原始 SQL 以解耦
        stmt = select(
            # 预期列: id, scope_type, scope_key, monthly_limit_usd, alert_threshold_pct, is_enabled
        ).select_from(
            # text("cost_budgets")
        )
        # 使用 text query 保持解耦
        from sqlalchemy import text as sa_text

        result = await session.execute(
            sa_text(
                "SELECT id, scope_type, scope_key, monthly_limit_usd, "
                "       alert_threshold_pct, is_enabled "
                "FROM cost_budgets "
                "WHERE scope_type = :st AND scope_key = :sk AND is_enabled = true"
            ),
            {"st": scope_type.value, "sk": scope_key},
        )
        row = result.mappings().first()
        if not row:
            return None

        monthly_limit = float(row["monthly_limit_usd"])
        threshold_pct = float(row["alert_threshold_pct"])
        usage_pct = (current_spend / monthly_limit * 100) if monthly_limit > 0 else 0

        return BudgetStatus(
            scope_type=scope_type,
            scope_key=scope_key,
            monthly_limit_usd=monthly_limit,
            current_spend_usd=current_spend,
            usage_pct=round(usage_pct, 1),
            alert_threshold_pct=threshold_pct,
            is_over_budget=current_spend >= monthly_limit,
        )

    # ── 告警评估 ───────────────────────────────────────────────────────

    async def evaluate_alerts(self) -> list[CostAlertInfo]:
        """扫描所有启用预算，检查是否需要触发告警。"""
        from sqlalchemy import text as sa_text

        alerts: list[CostAlertInfo] = []

        async with self._session_factory() as session:
            # 取所有启用预算
            result = await session.execute(
                sa_text(
                    "SELECT id, scope_type, scope_key, monthly_limit_usd, "
                    "       alert_threshold_pct "
                    "FROM cost_budgets WHERE is_enabled = true"
                ),
            )
            budgets = result.mappings().all()

            for b in budgets:
                try:
                    scope_type = BudgetScopeType(b["scope_type"])
                except ValueError:
                    logger.warning("Unknown scope_type=%s in budget id=%s, skipping", b["scope_type"], b["id"])
                    continue
                scope_key = b["scope_key"]
                monthly_limit = float(b["monthly_limit_usd"])
                threshold_pct = float(b["alert_threshold_pct"])

                # 本月已花费
                now = datetime.now(timezone.utc)
                month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

                # 构建参数化查询，避免 f-string 拼接 SQL
                where_clauses = ["\"StartedAtUtc\" >= :month_start"]
                params: dict = {"month_start": month_start}
                if scope_type == BudgetScopeType.MODEL:
                    where_clauses.append("\"ModelKey\" = :sk")
                    params["sk"] = scope_key
                where_sql = " AND ".join(where_clauses)

                spend_result = await session.execute(
                    sa_text(
                        f"SELECT COALESCE(SUM(\"TotalEstimatedCost\"), 0) "
                        f"FROM model_request_logs "
                        f"WHERE {where_sql}"
                    ),
                    params,
                )
                current_spend = float(spend_result.scalar_one())
                usage_pct = (current_spend / monthly_limit * 100) if monthly_limit > 0 else 0

                # 阈值告警
                if usage_pct >= threshold_pct:
                    alert_type = "exceeded" if current_spend >= monthly_limit else "threshold"
                    threshold_usd = monthly_limit * threshold_pct / 100

                    # 检查是否已有未确认告警（避免重复）
                    existing = await session.execute(
                        sa_text(
                            "SELECT id FROM cost_alerts "
                            "WHERE budget_id = :bid AND alert_type = :at "
                            "AND acknowledged_at_utc IS NULL"
                        ),
                        {"bid": b["id"], "at": alert_type},
                    )
                    if existing.first():
                        continue

                    # 插入新告警 — 必须显式生成 Snowflake ID
                    new_id = _next_snowflake_id()
                    await session.execute(
                        sa_text(
                            "INSERT INTO cost_alerts "
                            "(id, budget_id, alert_type, current_spend_usd, threshold_usd, triggered_at_utc, "
                            " created_at_utc, updated_at_utc) "
                            "VALUES (:id, :bid, :at, :spend, :threshold, NOW(), NOW(), NOW())"
                        ),
                        {
                            "id": new_id,
                            "bid": b["id"],
                            "at": alert_type,
                            "spend": current_spend,
                            "threshold": threshold_usd,
                        },
                    )

                    alerts.append(
                        CostAlertInfo(
                            id=new_id,
                            budget_id=b["id"],
                            scope_type=scope_type,
                            scope_key=scope_key,
                            alert_type=alert_type,
                            current_spend_usd=current_spend,
                            threshold_usd=threshold_usd,
                            triggered_at_utc=now,
                            acknowledged_at_utc=None,
                        )
                    )

            await session.commit()

        logger.info("Alert evaluation complete: %d new alerts triggered", len(alerts))
        return alerts

    # ── 告警查询 ───────────────────────────────────────────────────────

    async def list_alerts(
        self,
        *,
        acknowledged: bool | None = None,
        limit: int = 50,
    ) -> list[CostAlertInfo]:
        from sqlalchemy import text as sa_text

        async with self._session_factory() as session:
            where_clauses: list[str] = []
            params: dict = {"lim": limit}
            if acknowledged is not None:
                if acknowledged:
                    where_clauses.append("a.acknowledged_at_utc IS NOT NULL")
                else:
                    where_clauses.append("a.acknowledged_at_utc IS NULL")
            where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

            result = await session.execute(
                sa_text(
                    "SELECT a.id, a.budget_id, b.scope_type, b.scope_key, "
                    "       a.alert_type, a.current_spend_usd, a.threshold_usd, "
                    "       a.triggered_at_utc, a.acknowledged_at_utc "
                    "FROM cost_alerts a "
                    "JOIN cost_budgets b ON b.id = a.budget_id "
                    f"{where_sql} "
                    "ORDER BY a.triggered_at_utc DESC "
                    "LIMIT :lim"
                ),
                params,
            )
            return [
                CostAlertInfo(
                    id=row["id"],
                    budget_id=row["budget_id"],
                    scope_type=_safe_scope_type(row["scope_type"]),
                    scope_key=row["scope_key"],
                    alert_type=row["alert_type"],
                    current_spend_usd=float(row["current_spend_usd"]),
                    threshold_usd=float(row["threshold_usd"]),
                    triggered_at_utc=row["triggered_at_utc"],
                    acknowledged_at_utc=row["acknowledged_at_utc"],
                )
                for row in result.mappings().all()
            ]

    async def acknowledge_alert(self, alert_id: int) -> bool:
        from sqlalchemy import text as sa_text

        async with self._session_factory() as session:
            result = await session.execute(
                sa_text(
                    "UPDATE cost_alerts SET acknowledged_at_utc = NOW(), "
                    "updated_at_utc = NOW() "
                    "WHERE id = :aid AND acknowledged_at_utc IS NULL"
                ),
                {"aid": alert_id},
            )
            await session.commit()
            return result.rowcount > 0
