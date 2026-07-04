"""ConnectionProfileService — CRUD for LLM connection profiles."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.crud import create_entity, list_entities
from ..models import LlmConnectionProfile
from ._base import BaseCatalogService


class ConnectionProfileService(BaseCatalogService):
    """CRUD operations for :class:`LlmConnectionProfile`."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db)

    # ── CRUD ─────────────────────────────────────────────────────

    async def list_connection_profiles(
        self,
        page: int = 1,
        page_size: int = 20,
        provider: str | None = None,
        is_enabled: str | None = None,
    ) -> tuple[list[dict], int]:
        filters: dict[str, Any] = {}
        if provider:
            filters["provider"] = provider
        if is_enabled and is_enabled != "all":
            filters["is_enabled"] = is_enabled == "true"
        items, total = await list_entities(
            self._db, LlmConnectionProfile,
            page=page, page_size=page_size, filters=filters or None,
        )
        return [self._to_response(i) for i in items], total

    async def get_connection_profile(self, profile_key: str) -> dict:
        return self._to_response(
            await self._get_by_key(LlmConnectionProfile, "profile_key", profile_key)
        )

    async def create_connection_profile(self, **data: Any) -> dict:
        item = await create_entity(self._db, LlmConnectionProfile, **data)
        await self._db.commit()
        await self._db.refresh(item)
        return self._to_response(item)

    async def update_connection_profile(self, profile_key: str, **data: Any) -> dict:
        item = await self._get_by_key(LlmConnectionProfile, "profile_key", profile_key)
        for k, v in data.items():
            setattr(item, k, v)
        await self._db.commit()
        await self._db.refresh(item)
        return self._to_response(item)

    async def delete_connection_profile(self, profile_key: str) -> None:
        item = await self._get_by_key(LlmConnectionProfile, "profile_key", profile_key)
        await self._db.delete(item)
        await self._db.commit()

    # ── Provider Models ──────────────────────────────────────────

    async def get_provider_models(self, profile_key: str) -> dict:
        profile = await self._get_by_key(LlmConnectionProfile, "profile_key", profile_key)
        return {
            "connectionProfileKey": profile.profile_key,
            "provider": profile.provider,
            "models": [],
            "deployments": [],
        }
