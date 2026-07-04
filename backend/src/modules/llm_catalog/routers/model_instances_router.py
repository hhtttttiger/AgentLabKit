"""Model Instances router — 5 standalone CRUD routes."""

from __future__ import annotations

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

from common.response import ok, paged
from ..dependencies import ModelInstanceServiceDep
from ..schemas import ModelInstanceCreate, ModelInstanceUpdate
from ._helpers import _encrypt_api_key, _refresh_catalog

router = APIRouter()


@router.get("/model-instances")
async def list_model_instances(
    svc: ModelInstanceServiceDep,
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    isEnabled: str | None = Query(None),
    isHealthy: str | None = Query(None),
    type: str | None = Query(None),
    modelKey: str | None = Query(None),
):
    items, total = await svc.list_model_instances(
        page=page, page_size=pageSize,
        is_enabled=isEnabled, is_healthy=isHealthy, type=type, model_key=modelKey,
    )
    return ok(paged(items, total, page, pageSize))


@router.get("/model-instances/{instance_key}")
async def get_model_instance(instance_key: str, svc: ModelInstanceServiceDep):
    return ok(await svc.get_model_instance(instance_key))


@router.post("/model-instances")
async def create_model_instance(body: ModelInstanceCreate, svc: ModelInstanceServiceDep, request: Request):
    data = body.model_dump(by_alias=False)
    if data.get("encrypted_api_key"):
        data["encrypted_api_key"] = _encrypt_api_key(request, data["encrypted_api_key"])
    result = await svc.create_model_instance(**data)
    await _refresh_catalog(request)
    return ok(result)


@router.put("/model-instances/{instance_key}")
async def update_model_instance(
    instance_key: str,
    body: ModelInstanceUpdate,
    svc: ModelInstanceServiceDep,
    request: Request,
):
    import traceback
    try:
        data = body.model_dump(by_alias=False, exclude_none=True)
        if data.get("api_key"):
            data["encrypted_api_key"] = _encrypt_api_key(request, data.pop("api_key"))
        result = await svc.update_model_instance(instance_key, **data)
        await _refresh_catalog(request)
        return ok(result)
    except Exception:
        return JSONResponse(
            {"success": False, "msg": "Internal error", "trace": traceback.format_exc()[-5000:]},
            status_code=500,
        )


@router.delete("/model-instances/{instance_key}")
async def delete_model_instance(instance_key: str, svc: ModelInstanceServiceDep, request: Request):
    await svc.delete_model_instance(instance_key)
    await _refresh_catalog(request)
    return ok(None)
