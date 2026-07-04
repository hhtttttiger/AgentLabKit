"""Models router — 9 routes (CRUD + options + nested instances/bindings)."""

from __future__ import annotations

from fastapi import APIRouter, Query, Request

from common.response import ok, paged
from ..dependencies import ModelServiceDep, ModelInstanceServiceDep, ModelBindingServiceDep
from ..schemas import (
    ModelCreate,
    ModelInstanceCreateByModel,
    ModelBindingCreateByModel,
    ModelUpdate,
)
from ._helpers import _encrypt_api_key, _refresh_catalog

router = APIRouter()


# ── Options ────────────────────────────────────────────────────

@router.get("/models/options")
async def list_model_options(svc: ModelServiceDep):
    return ok(await svc.list_model_options())


# ── CRUD ───────────────────────────────────────────────────────

@router.get("/models")
async def list_models(
    svc: ModelServiceDep,
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    isEnabled: str | None = Query(None),
    type: str | None = Query(None),
):
    items, total = await svc.list_models(
        page=page, page_size=pageSize, is_enabled=isEnabled, type=type,
    )
    return ok(paged(items, total, page, pageSize))


@router.get("/models/{model_key}")
async def get_model(model_key: str, svc: ModelServiceDep):
    return ok(await svc.get_model(model_key))


@router.post("/models")
async def create_model(body: ModelCreate, svc: ModelServiceDep, request: Request):
    result = await svc.create_model(**body.model_dump(by_alias=False))
    await _refresh_catalog(request)
    return ok(result)


@router.put("/models/{model_key}")
async def update_model(model_key: str, body: ModelUpdate, svc: ModelServiceDep, request: Request):
    result = await svc.update_model(
        model_key, **body.model_dump(by_alias=False, exclude_none=True),
    )
    await _refresh_catalog(request)
    return ok(result)


@router.delete("/models/{model_key}")
async def delete_model(model_key: str, svc: ModelServiceDep, request: Request):
    result = await svc.delete_model(model_key)
    await _refresh_catalog(request)
    return ok(result)


# ── Nested: instances under model ──────────────────────────────

@router.get("/models/{model_key}/instances")
async def list_model_instances_by_model(
    model_key: str,
    svc: ModelInstanceServiceDep,
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
):
    items, total = await svc.list_by_model(
        model_key, page=page, page_size=pageSize,
    )
    return ok(paged(items, total, page, pageSize))


@router.post("/models/{model_key}/instances")
async def create_model_instance_by_model(
    model_key: str,
    body: ModelInstanceCreateByModel,
    svc: ModelInstanceServiceDep,
    request: Request,
):
    data = body.model_dump(by_alias=False)
    api_key = data.pop("api_key", None)
    if api_key is not None:
        data["encrypted_api_key"] = _encrypt_api_key(request, api_key)
    result = await svc.create_by_model(model_key, **data)
    await _refresh_catalog(request)
    return ok(result)


# ── Nested: bindings under model ───────────────────────────────

@router.post("/models/{model_key}/bindings")
async def create_model_binding_by_model(
    model_key: str,
    body: ModelBindingCreateByModel,
    svc: ModelBindingServiceDep,
    request: Request,
):
    result = await svc.create_by_model(model_key, **body.model_dump(by_alias=False))
    await _refresh_catalog(request)
    return ok(result)
