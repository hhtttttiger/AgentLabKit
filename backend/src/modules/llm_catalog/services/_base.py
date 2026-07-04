"""Base class for llm_catalog services — shared helpers and schema mapping."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.errors import NotFoundError
from ..models import (
    LlmConnectionProfile,
    LlmFeature,
    LlmModel,
    LlmModelBinding,
    LlmModelFeature,
    LlmModelInstance,
)
from ..schemas import (
    ConnectionProfileResponse,
    FeatureResponse,
    ModelBindingResponse,
    ModelFeatureResponse,
    ModelInstanceResponse,
    ModelResponse,
)


class BaseCatalogService:
    """Shared helpers for all llm_catalog entity services."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # ── Response-schema mapping ──────────────────────────────────

    _RESPONSE_MAP = {
        LlmConnectionProfile: ConnectionProfileResponse,
        LlmModel: ModelResponse,
        LlmModelInstance: ModelInstanceResponse,
        LlmFeature: FeatureResponse,
        LlmModelBinding: ModelBindingResponse,
    }

    # ── Shared helpers ───────────────────────────────────────────

    async def _get_by_key(self, model: type, key_col: str, key_val: str):
        """Fetch a single row by its unique key column, or raise ``NotFoundError``."""
        col = getattr(model, key_col)
        result = await self._db.execute(select(model).where(col == key_val))
        obj = result.scalar_one_or_none()
        if obj is None:
            raise NotFoundError(model.__name__, key_val)
        return obj

    @classmethod
    def _to_response(
        cls,
        obj: Any,
        connection_profile_key: str = "",
        model_key: str = "",
    ) -> dict:
        """Convert an ORM object to a response dict via its Pydantic schema.

        Sensitive fields like ``encrypted_api_key`` are excluded.
        """
        schema_cls = cls._RESPONSE_MAP.get(type(obj))
        if schema_cls is None:
            return {c.key: getattr(obj, c.key) for c in obj.__table__.columns}
        if schema_cls is ModelInstanceResponse:
            return schema_cls(
                **{c.key: getattr(obj, c.key) for c in obj.__table__.columns if c.key != "encrypted_api_key"},
                model_key=model_key,
                has_api_key=bool(getattr(obj, "encrypted_api_key", None)),
            ).model_dump()
        if schema_cls is ModelResponse:
            data = schema_cls.model_validate(obj).model_dump()
            data["connectionProfileKey"] = connection_profile_key
            return data
        return schema_cls.model_validate(obj).model_dump()

    @staticmethod
    def _to_model_feature_response(
        mf: LlmModelFeature,
        model_key: str,
        feature: LlmFeature,
    ) -> dict:
        """Convert a ModelFeature junction row + feature info into a response dict."""
        return ModelFeatureResponse(
            model_key=model_key,
            feature_key=feature.feature_key,
            display_name=feature.display_name,
            value_type=feature.value_type,
            allowed_values_json=feature.allowed_values_json,
            is_supported=mf.is_supported,
            value_json=mf.value_json,
            source=mf.source,
            remark=mf.remark,
        ).model_dump()

    async def _resolve_instance_model_keys(self, instances: list) -> dict[int, str]:
        """Batch-resolve model_id → model_key for a list of instance ORM objects."""
        if not instances:
            return {}
        model_ids = {i.model_id for i in instances}
        models = (
            await self._db.execute(
                select(LlmModel.id, LlmModel.model_key).where(LlmModel.id.in_(model_ids))
            )
        ).all()
        return {m.id: m.model_key for m in models}
