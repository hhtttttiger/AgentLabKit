"""ModelService — CRUD for LLM models with batch-resolved nested entities."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.crud import create_entity, list_entities
from ..models import (
    LlmConnectionProfile,
    LlmFeature,
    LlmModel,
    LlmModelBinding,
    LlmModelFeature,
    LlmModelInstance,
)
from ._base import BaseCatalogService


class ModelService(BaseCatalogService):
    """CRUD for :class:`LlmModel`, including batch resolution of nested
    instances, bindings, and features for list/get endpoints."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db)

    # ── Options ──────────────────────────────────────────────────

    async def list_model_options(self) -> list[dict]:
        result = await self._db.execute(
            select(LlmModel.model_key, LlmModel.display_name)
            .where(LlmModel.is_enabled == True)
            .order_by(LlmModel.model_key)
        )
        return [{"value": r.model_key, "label": r.display_name or r.model_key} for r in result.all()]

    # ── CRUD ─────────────────────────────────────────────────────

    async def list_models(
        self,
        page: int = 1,
        page_size: int = 20,
        is_enabled: str | None = None,
        type: str | None = None,
    ) -> tuple[list[dict], int]:
        filters: dict[str, Any] = {}
        if is_enabled and is_enabled != "all":
            filters["is_enabled"] = is_enabled == "true"
        if type:
            filters["type"] = type
        items, total = await list_entities(
            self._db, LlmModel,
            page=page, page_size=page_size, filters=filters or None,
        )

        # Batch-resolve profile keys
        profile_ids = {item.connection_profile_id for item in items}
        if profile_ids:
            profiles = (
                await self._db.execute(
                    select(LlmConnectionProfile).where(LlmConnectionProfile.id.in_(profile_ids))
                )
            ).scalars()
            profile_map = {p.id: p.profile_key for p in profiles}
        else:
            profile_map = {}

        model_ids = [i.id for i in items]
        count_map: dict[int, int] = {}
        healthy_map: dict[int, int] = {}
        bindings_count_map: dict[int, int] = {}
        features_map: dict[int, list] = {}

        if model_ids:
            # Instance counts and health
            all_instances = (
                await self._db.execute(
                    select(LlmModelInstance.model_id, LlmModelInstance.is_healthy).where(
                        LlmModelInstance.model_id.in_(model_ids)
                    )
                )
            ).all()
            for model_id, is_healthy in all_instances:
                count_map[model_id] = count_map.get(model_id, 0) + 1
                if is_healthy:
                    healthy_map[model_id] = healthy_map.get(model_id, 0) + 1

            # Binding counts
            all_bindings = (
                await self._db.execute(
                    select(LlmModelBinding.model_id).where(LlmModelBinding.model_id.in_(model_ids))
                )
            ).all()
            for (model_id,) in all_bindings:
                bindings_count_map[model_id] = bindings_count_map.get(model_id, 0) + 1

            # Model-features with feature definitions
            all_mf = (
                await self._db.execute(
                    select(LlmModelFeature, LlmFeature)
                    .join(LlmFeature, LlmModelFeature.feature_id == LlmFeature.id)
                    .where(LlmModelFeature.model_id.in_(model_ids))
                )
            ).all()
            for mf, feat in all_mf:
                m = next((it for it in items if it.id == mf.model_id), None)
                model_k = m.model_key if m else ""
                if mf.model_id not in features_map:
                    features_map[mf.model_id] = []
                features_map[mf.model_id].append(
                    self._to_model_feature_response(mf, model_k, feat)
                )

        return (
            [
                {
                    **self._to_response(i, profile_map.get(i.connection_profile_id, "")),
                    "instanceCount": count_map.get(i.id, 0),
                    "healthyInstanceCount": healthy_map.get(i.id, 0),
                    "bindingsCount": bindings_count_map.get(i.id, 0),
                    "features": features_map.get(i.id, []),
                }
                for i in items
            ],
            total,
        )

    async def get_model(self, model_key: str) -> dict:
        item = await self._get_by_key(LlmModel, "model_key", model_key)

        # Resolve profile key
        profile = (
            await self._db.execute(
                select(LlmConnectionProfile).where(LlmConnectionProfile.id == item.connection_profile_id)
            )
        ).scalar_one_or_none()
        profile_key = profile.profile_key if profile else ""

        # Fetch nested instances
        instances_result = await self._db.execute(
            select(LlmModelInstance).where(LlmModelInstance.model_id == item.id)
        )
        instances = instances_result.scalars().all()
        instance_responses = [self._to_response(i, model_key=item.model_key) for i in instances]
        instance_count = len(instances)
        healthy_instance_count = sum(1 for i in instances if i.is_healthy)

        # Fetch nested bindings
        bindings_result = await self._db.execute(
            select(LlmModelBinding).where(LlmModelBinding.model_id == item.id)
        )
        bindings = bindings_result.scalars().all()
        binding_responses = [{**self._to_response(b), "modelKey": item.model_key} for b in bindings]

        # Fetch nested features (junction + feature definitions)
        features_result = await self._db.execute(
            select(LlmModelFeature, LlmFeature)
            .join(LlmFeature, LlmModelFeature.feature_id == LlmFeature.id)
            .where(LlmModelFeature.model_id == item.id)
        )
        feature_rows = features_result.all()
        feature_responses = [
            self._to_model_feature_response(mf, item.model_key, feat)
            for mf, feat in feature_rows
        ]

        return {
            **self._to_response(item, connection_profile_key=profile_key),
            "instances": instance_responses,
            "bindings": binding_responses,
            "features": feature_responses,
            "instanceCount": instance_count,
            "healthyInstanceCount": healthy_instance_count,
        }

    async def create_model(self, **data: Any) -> dict:
        profile_key: str = data.pop("connection_profile_key")
        profile = await self._get_by_key(LlmConnectionProfile, "profile_key", profile_key)
        data["connection_profile_id"] = profile.id
        item = await create_entity(self._db, LlmModel, **data)
        await self._db.commit()
        await self._db.refresh(item)
        return self._to_response(item, profile.profile_key)

    async def update_model(self, model_key: str, **data: Any) -> dict:
        item = await self._get_by_key(LlmModel, "model_key", model_key)
        profile = None
        if "connection_profile_key" in data:
            profile_key: str = data.pop("connection_profile_key")
            profile = await self._get_by_key(LlmConnectionProfile, "profile_key", profile_key)
            data["connection_profile_id"] = profile.id
            item.connection_profile_id = profile.id
        for k, v in data.items():
            setattr(item, k, v)
        await self._db.commit()
        await self._db.refresh(item)
        if profile is None:
            profile = (
                await self._db.execute(
                    select(LlmConnectionProfile).where(
                        LlmConnectionProfile.id == item.connection_profile_id
                    )
                )
            ).scalar_one_or_none()
        return self._to_response(item, profile.profile_key if profile else "")

    async def delete_model(self, model_key: str) -> dict:
        item = await self._get_by_key(LlmModel, "model_key", model_key)
        await self._db.delete(item)
        await self._db.commit()
        return {"modelKey": model_key, "deleted": True}
