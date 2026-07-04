"""ModelBindingService — CRUD for LLM model bindings (standalone + nested)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.crud import create_entity, list_entities
from ..models import LlmModel, LlmModelBinding
from ._base import BaseCatalogService


class ModelBindingService(BaseCatalogService):
    """CRUD for :class:`LlmModelBinding`, both standalone and nested under a model."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db)

    # ── Nested (under model) ─────────────────────────────────────

    async def create_by_model(self, model_key: str, **data: Any) -> dict:
        model = await self._get_by_key(LlmModel, "model_key", model_key)
        data["model_id"] = model.id
        item = await create_entity(self._db, LlmModelBinding, **data)
        await self._db.commit()
        await self._db.refresh(item)
        return self._to_response(item)

    # ── Standalone CRUD ──────────────────────────────────────────

    async def list_model_bindings(
        self,
        page: int = 1,
        page_size: int = 20,
        is_enabled: str | None = None,
        capability: str | None = None,
        model_key: str | None = None,
    ) -> tuple[list[dict], int]:
        filters: dict[str, Any] = {}
        if is_enabled and is_enabled != "all":
            filters["is_enabled"] = is_enabled == "true"
        if capability:
            filters["capability"] = capability
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
            self._db, LlmModelBinding,
            page=page, page_size=page_size, filters=filters or None,
        )
        # Batch-fetch model keys
        model_ids = {i.model_id for i in items}
        if model_ids:
            models = (
                await self._db.execute(
                    select(LlmModel.id, LlmModel.model_key).where(LlmModel.id.in_(model_ids))
                )
            ).all()
            model_map = {m.id: m.model_key for m in models}
        else:
            model_map = {}
        return (
            [
                {**self._to_response(i), "modelKey": model_map.get(i.model_id, "")}
                for i in items
            ],
            total,
        )

    async def get_model_binding(self, binding_key: str) -> dict:
        item = await self._get_by_key(LlmModelBinding, "binding_key", binding_key)
        model_key_val = (
            await self._db.execute(
                select(LlmModel.model_key).where(LlmModel.id == item.model_id)
            )
        ).scalar_one_or_none()
        return {**self._to_response(item), "modelKey": model_key_val or ""}

    async def create_model_binding(self, **data: Any) -> dict:
        # Resolve model_key → model_id if model_id not provided
        if data.get("model_id") is None:
            model_key_val: str = data.pop("model_key")
            model = await self._get_by_key(LlmModel, "model_key", model_key_val)
            data["model_id"] = model.id
        else:
            data.pop("model_key", None)
        item = await create_entity(self._db, LlmModelBinding, **data)
        await self._db.commit()
        await self._db.refresh(item)
        resolved_key = (
            await self._db.execute(
                select(LlmModel.model_key).where(LlmModel.id == item.model_id)
            )
        ).scalar_one_or_none()
        return {**self._to_response(item), "modelKey": resolved_key or ""}

    async def update_model_binding(self, binding_key: str, **data: Any) -> dict:
        item = await self._get_by_key(LlmModelBinding, "binding_key", binding_key)
        for k, v in data.items():
            setattr(item, k, v)
        await self._db.commit()
        await self._db.refresh(item)
        resolved_key = (
            await self._db.execute(
                select(LlmModel.model_key).where(LlmModel.id == item.model_id)
            )
        ).scalar_one_or_none()
        return {**self._to_response(item), "modelKey": resolved_key or ""}

    async def delete_model_binding(self, binding_key: str) -> None:
        item = await self._get_by_key(LlmModelBinding, "binding_key", binding_key)
        await self._db.delete(item)
        await self._db.commit()
