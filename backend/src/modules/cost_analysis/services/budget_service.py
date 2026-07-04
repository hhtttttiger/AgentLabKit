"""Budget CRUD operations."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.errors import NotFoundError
from ..models import CostBudget
from ..schemas import BudgetResponse


class BudgetService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def list_budgets(self) -> list[dict]:
        result = await self._db.execute(
            select(CostBudget).order_by(CostBudget.scope_type, CostBudget.scope_key)
        )
        return [self._to_view(b) for b in result.scalars().all()]

    async def create_budget(self, **kwargs) -> dict:
        budget = CostBudget(**kwargs)
        self._db.add(budget)
        await self._db.flush()
        await self._db.refresh(budget)
        await self._db.commit()
        return self._to_view(budget)

    async def update_budget(self, budget_id: int, **kwargs) -> dict:
        result = await self._db.execute(select(CostBudget).where(CostBudget.id == budget_id))
        budget = result.scalar_one_or_none()
        if not budget:
            raise NotFoundError("Budget", str(budget_id))
        for k, v in kwargs.items():
            if v is not None:
                setattr(budget, k, v)
        await self._db.flush()
        await self._db.commit()
        return self._to_view(budget)

    async def delete_budget(self, budget_id: int) -> None:
        result = await self._db.execute(select(CostBudget).where(CostBudget.id == budget_id))
        budget = result.scalar_one_or_none()
        if not budget:
            raise NotFoundError("Budget", str(budget_id))
        await self._db.delete(budget)
        await self._db.commit()

    @staticmethod
    def _to_view(b: CostBudget) -> dict:
        return BudgetResponse(
            id=b.id,
            scope_type=b.scope_type,
            scope_key=b.scope_key,
            monthly_limit_usd=b.monthly_limit_usd,
            alert_threshold_pct=b.alert_threshold_pct,
            is_enabled=b.is_enabled,
            created_at_utc=b.created_at_utc,
            updated_at_utc=b.updated_at_utc,
        ).model_dump()
