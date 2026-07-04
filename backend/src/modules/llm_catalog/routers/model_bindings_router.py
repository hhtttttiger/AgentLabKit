"""Model Bindings router — 5 standalone CRUD routes."""

from __future__ import annotations

from fastapi import APIRouter, Query, Request

from common.response import ok, paged
from ..dependencies import ModelBindingServiceDep
from ..schemas import ModelBindingCreate, ModelBindingUpdate
from ._helpers import _refresh_catalog

router = APIRouter()


@router.get("/model-bindings")
async def list_model_bindings(
    svc: ModelBindingServiceDep,
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    isEnabled: str | None = Query(None),
    capability: str | None = Query(None),
    modelKey: str | None = Query(None),
):
    items, total = await svc.list_model_bindings(
        page=page, page_size=pageSize,
        is_enabled=isEnabled, capability=capability, model_key=modelKey,
    )
    return ok(paged(items, total, page, pageSize))


@router.get("/model-bindings/{binding_key}")
async def get_model_binding(binding_key: str, svc: ModelBindingServiceDep):
    return ok(await svc.get_model_binding(binding_key))


@router.post("/model-bindings")
async def create_model_binding(body: ModelBindingCreate, svc: ModelBindingServiceDep, request: Request):
    result = await svc.create_model_binding(**body.model_dump(by_alias=False))
    await _refresh_catalog(request)
    return ok(result)


@router.put("/model-bindings/{binding_key}")
async def update_model_binding(
    binding_key: str,
    body: ModelBindingUpdate,
    svc: ModelBindingServiceDep,
    request: Request,
):
    result = await svc.update_model_binding(
        binding_key, **body.model_dump(by_alias=False, exclude_none=True),
    )
    await _refresh_catalog(request)
    return ok(result)


@router.delete("/model-bindings/{binding_key}")
async def delete_model_binding(binding_key: str, svc: ModelBindingServiceDep, request: Request):
    await svc.delete_model_binding(binding_key)
    await _refresh_catalog(request)
    return ok(None)
