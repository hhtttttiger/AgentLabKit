"""Model Features router — 2 junction routes (upsert, delete)."""

from __future__ import annotations

from fastapi import APIRouter, Request

from common.response import ok
from ..dependencies import ModelFeatureServiceDep
from ..schemas import ModelFeatureUpsert
from ._helpers import _refresh_catalog

router = APIRouter()


@router.put("/models/{model_key}/features/{feature_key}")
async def upsert_model_feature(
    model_key: str,
    feature_key: str,
    body: ModelFeatureUpsert,
    svc: ModelFeatureServiceDep,
    request: Request,
):
    result = await svc.upsert_model_feature(
        model_key, feature_key, **body.model_dump(by_alias=False),
    )
    await _refresh_catalog(request)
    return ok(result)


@router.delete("/models/{model_key}/features/{feature_key}")
async def delete_model_feature(
    model_key: str,
    feature_key: str,
    svc: ModelFeatureServiceDep,
    request: Request,
):
    await svc.delete_model_feature(model_key, feature_key)
    await _refresh_catalog(request)
    return ok(None)
