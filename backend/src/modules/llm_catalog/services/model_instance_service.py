"""ModelInstanceService — CRUD for LLM model instances (standalone + nested)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from common.crud import create_entity, list_entities
from ..models import LlmModel, LlmModelInstance
from ._base import BaseCatalogService


class ModelInstanceService(BaseCatalogService):
    """CRUD for :class:`LlmModelInstance`, both standalone and nested under a model."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db)

    # ── Nested (under model) ─────────────────────────────────────

    async def list_by_model(
        self, model_key: str, page: int = 1, page_size: int = 20,
    ) -> tuple[list[dict], int]:
        model = await self._get_by_key(LlmModel, "model_key", model_key)
        total_q = select(func.count()).select_from(LlmModelInstance).where(
            LlmModelInstance.model_id == model.id
        )
        total = (await self._db.execute(total_q)).scalar() or 0
        result = await self._db.execute(
            select(LlmModelInstance)
            .where(LlmModelInstance.model_id == model.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        items = result.scalars().all()
        return (
            [self._to_response(i, model_key=model.model_key) for i in items],
            total,
        )

    async def create_by_model(self, model_key: str, **data: Any) -> dict:
        model = await self._get_by_key(LlmModel, "model_key", model_key)
        data["model_id"] = model.id
        item = await create_entity(self._db, LlmModelInstance, **data)
        await self._db.commit()
        await self._db.refresh(item)
        return self._to_response(item, model_key=model.model_key)

    # ── Standalone CRUD ──────────────────────────────────────────

    async def list_model_instances(
        self,
        page: int = 1,
        page_size: int = 20,
        is_enabled: str | None = None,
        is_healthy: str | None = None,
        type: str | None = None,  # noqa: ARG002 — accepted but not filtered (preserving router behaviour)
        model_key: str | None = None,
    ) -> tuple[list[dict], int]:
        filters: dict[str, Any] = {}
        if is_enabled and is_enabled != "all":
            filters["is_enabled"] = is_enabled == "true"
        if is_healthy and is_healthy != "all":
            filters["is_healthy"] = is_healthy == "true"
        if model_key:
            model = (
                await self._db.execute(
                    select(LlmModel.id).where(LlmModel.model_key == model_key)
                )
            ).scalar_one_or_none()
            if model:
                filters["model_id"] = model
            else:
                return [], 0
        items, total = await list_entities(
            self._db, LlmModelInstance,
            page=page, page_size=page_size, filters=filters or None,
        )
        model_keys = await self._resolve_instance_model_keys(items)
        return (
            [self._to_response(i, model_key=model_keys.get(i.model_id, "")) for i in items],
            total,
        )

    async def get_model_instance(self, instance_key: str) -> dict:
        item = await self._get_by_key(LlmModelInstance, "instance_key", instance_key)
        model = (
            await self._db.execute(
                select(LlmModel.model_key).where(LlmModel.id == item.model_id)
            )
        ).scalar_one_or_none()
        return self._to_response(item, model_key=model or "")

    async def create_model_instance(self, **data: Any) -> dict:
        item = await create_entity(self._db, LlmModelInstance, **data)
        await self._db.commit()
        await self._db.refresh(item)
        model = (
            await self._db.execute(
                select(LlmModel.model_key).where(LlmModel.id == item.model_id)
            )
        ).scalar_one_or_none()
        return self._to_response(item, model_key=model or "")

    async def update_model_instance(self, instance_key: str, **data: Any) -> dict:
        item = await self._get_by_key(LlmModelInstance, "instance_key", instance_key)
        for k, v in data.items():
            setattr(item, k, v)
        await self._db.commit()
        await self._db.refresh(item)
        model = (
            await self._db.execute(
                select(LlmModel.model_key).where(LlmModel.id == item.model_id)
            )
        ).scalar_one_or_none()
        return self._to_response(item, model_key=model or "")
    async def delete_model_instance(self, instance_key: str) -> None:
        item = await self._get_by_key(LlmModelInstance, "instance_key", instance_key)
        await self._db.delete(item)
        await self._db.commit()
