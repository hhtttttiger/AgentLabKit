"""Features router — 5 CRUD routes."""

from __future__ import annotations

from fastapi import APIRouter, Query, Request

from common.response import ok, paged
from ..dependencies import FeatureServiceDep
from ..schemas import FeatureCreate, FeatureUpdate
from ._helpers import _refresh_catalog

router = APIRouter()


@router.get("/features")
async def list_features(
    svc: FeatureServiceDep,
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    isEnabled: str | None = Query(None),
    valueType: str | None = Query(None),
    isFilterable: str | None = Query(None),
    isRoutable: str | None = Query(None),
):
    items, total = await svc.list_features(
        page=page, page_size=pageSize,
        is_enabled=isEnabled, value_type=valueType,
        is_filterable=isFilterable, is_routable=isRoutable,
    )
    return ok(paged(items, total, page, pageSize))


@router.get("/features/{feature_key}")
async def get_feature(feature_key: str, svc: FeatureServiceDep):
    return ok(await svc.get_feature(feature_key))


@router.post("/features")
async def create_feature(body: FeatureCreate, svc: FeatureServiceDep, request: Request):
    result = await svc.create_feature(**body.model_dump(by_alias=False))
    await _refresh_catalog(request)
    return ok(result)


@router.put("/features/{feature_key}")
async def update_feature(feature_key: str, body: FeatureUpdate, svc: FeatureServiceDep, request: Request):
    result = await svc.update_feature(
        feature_key, **body.model_dump(by_alias=False, exclude_none=True),
    )
    await _refresh_catalog(request)
    return ok(result)


@router.delete("/features/{feature_key}")
async def delete_feature(feature_key: str, svc: FeatureServiceDep, request: Request):
    result = await svc.delete_feature(feature_key)
    await _refresh_catalog(request)
    return ok(result)
