"""OptionsService — read-only option lists for dropdowns / selectors."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import LlmConnectionProfile, LlmFeature, LlmModel
from ._base import BaseCatalogService


class OptionsService(BaseCatalogService):
    """Read-only option lists consumed by frontend dropdowns / selectors."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db)

    async def connection_profile_options(self) -> list[dict]:
        result = await self._db.execute(select(LlmConnectionProfile))
        items = result.scalars().all()
        return [
            {
                "profileKey": i.profile_key,
                "displayName": i.display_name,
                "provider": i.provider,
                "baseUrl": i.base_url,
                "webSocketBaseUrl": i.websocket_base_url,
                "isEnabled": i.is_enabled,
            }
            for i in items
        ]

    async def model_options(self) -> list[dict]:
        result = await self._db.execute(select(LlmModel))
        items = result.scalars().all()
        return [
            {
                "modelKey": i.model_key,
                "modelName": i.model_name,
                "displayName": i.display_name,
                "isEnabled": i.is_enabled,
            }
            for i in items
        ]

    async def feature_options(self) -> list[dict]:
        result = await self._db.execute(select(LlmFeature))
        items = result.scalars().all()
        return [
            {
                "featureKey": i.feature_key,
                "displayName": i.display_name,
                "valueType": i.value_type,
                "allowedValuesJson": i.allowed_values_json,
                "isEnabled": i.is_enabled,
                "isFilterable": i.is_filterable,
                "isRoutable": i.is_routable,
            }
            for i in items
        ]
