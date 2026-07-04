from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Float, Index, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from alkit_db.base import EntityBase


class CostBudget(EntityBase):
    """成本预算配置。"""
    __tablename__ = "cost_budgets"

    scope_type: Mapped[str] = mapped_column(String(32), index=True)  # global / model / agent / user
    scope_key: Mapped[str] = mapped_column(String(128), default="*")
    monthly_limit_usd: Mapped[float] = mapped_column(Float, default=0)
    alert_threshold_pct: Mapped[float] = mapped_column(Float, default=80)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    extra_json: Mapped[dict] = mapped_column(JSONB, default=dict, server_default=text("'{}'::jsonb"))

    __table_args__ = (
        Index("ix_cost_budgets_scope", "scope_type", "scope_key", unique=True),
    )


class CostAlert(EntityBase):
    """预算告警记录。"""
    __tablename__ = "cost_alerts"

    budget_id: Mapped[int] = mapped_column(BigInteger, index=True)
    alert_type: Mapped[str] = mapped_column(String(32))  # threshold / exceeded
    current_spend_usd: Mapped[float] = mapped_column(Float)
    threshold_usd: Mapped[float] = mapped_column(Float)
    triggered_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    acknowledged_at_utc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_cost_alerts_unacked", "acknowledged_at_utc"),
    )
