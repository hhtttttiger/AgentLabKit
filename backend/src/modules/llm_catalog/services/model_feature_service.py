"""ModelFeatureService — junction table operations for model-feature associations."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.crud import create_entity
from common.errors import NotFoundError
from ..models import LlmFeature, LlmModel, LlmModelFeature
from ._base import BaseCatalogService


class ModelFeatureService(BaseCatalogService):
    """Junction-table operations for :class:`LlmModelFeature`."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db)

    async def upsert_model_feature(
        self, model_key: str, feature_key: str, **data: Any,
    ) -> dict:
        model = await self._get_by_key(LlmModel, "model_key", model_key)
        feature = await self._get_by_key(LlmFeature, "feature_key", feature_key)
        result = await self._db.execute(
            select(LlmModelFeature).where(
                LlmModelFeature.model_id == model.id,
                LlmModelFeature.feature_id == feature.id,
            )
        )
        mf = result.scalar_one_or_none()
        if mf is None:
            mf = await create_entity(
                self._db,
                LlmModelFeature,
                model_id=model.id,
                feature_id=feature.id,
                **data,
            )
        else:
            for k, v in data.items():
                setattr(mf, k, v)
            await self._db.flush()
        await self._db.commit()
        await self._db.refresh(mf)
        return self._to_model_feature_response(mf, model.model_key, feature)

    async def delete_model_feature(self, model_key: str, feature_key: str) -> None:
        model = await self._get_by_key(LlmModel, "model_key", model_key)
        feature = await self._get_by_key(LlmFeature, "feature_key", feature_key)
        result = await self._db.execute(
            select(LlmModelFeature).where(
                LlmModelFeature.model_id == model.id,
                LlmModelFeature.feature_id == feature.id,
            )
        )
        mf = result.scalar_one_or_none()
        if mf is None:
            raise NotFoundError("ModelFeature", f"{model_key}/{feature_key}")
        await self._db.delete(mf)
        await self._db.commit()
