"""FeatureService — CRUD for LLM features (capability flags, routing hints)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from common.crud import create_entity, list_entities
from ..models import LlmFeature
from ._base import BaseCatalogService


class FeatureService(BaseCatalogService):
    """CRUD for :class:`LlmFeature`."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db)

    async def list_features(
        self,
        page: int = 1,
        page_size: int = 20,
        is_enabled: str | None = None,
        value_type: str | None = None,
        is_filterable: str | None = None,
        is_routable: str | None = None,
    ) -> tuple[list[dict], int]:
        filters: dict[str, Any] = {}
        if is_enabled and is_enabled != "all":
            filters["is_enabled"] = is_enabled == "true"
        if value_type:
            filters["value_type"] = value_type
        if is_filterable and is_filterable != "all":
            filters["is_filterable"] = is_filterable == "true"
        if is_routable and is_routable != "all":
            filters["is_routable"] = is_routable == "true"
        items, total = await list_entities(
            self._db, LlmFeature,
            page=page, page_size=page_size, filters=filters or None,
        )
        return [self._to_response(i) for i in items], total

    async def get_feature(self, feature_key: str) -> dict:
        return self._to_response(
            await self._get_by_key(LlmFeature, "feature_key", feature_key)
        )

    async def create_feature(self, **data: Any) -> dict:
        item = await create_entity(self._db, LlmFeature, **data)
        await self._db.commit()
        await self._db.refresh(item)
        return self._to_response(item)

    async def update_feature(self, feature_key: str, **data: Any) -> dict:
        item = await self._get_by_key(LlmFeature, "feature_key", feature_key)
        for k, v in data.items():
            setattr(item, k, v)
        await self._db.commit()
        await self._db.refresh(item)
        return self._to_response(item)

    async def delete_feature(self, feature_key: str) -> dict:
        item = await self._get_by_key(LlmFeature, "feature_key", feature_key)
        await self._db.delete(item)
        await self._db.commit()
        return {"featureKey": feature_key, "deleted": True}
