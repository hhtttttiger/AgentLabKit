"""Connection Profiles router — 6 routes."""

from __future__ import annotations

from fastapi import APIRouter, Query, Request

from common.response import ok, paged
from ..dependencies import ConnectionProfileServiceDep
from ..schemas import ConnectionProfileCreate, ConnectionProfileUpdate
from ._helpers import _refresh_catalog

router = APIRouter()


@router.get("/connection-profiles")
async def list_connection_profiles(
    svc: ConnectionProfileServiceDep,
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    provider: str | None = Query(None),
    isEnabled: str | None = Query(None),
):
    items, total = await svc.list_connection_profiles(
        page=page, page_size=pageSize, provider=provider, is_enabled=isEnabled,
    )
    return ok(paged(items, total, page, pageSize))


@router.get("/connection-profiles/{profile_key}")
async def get_connection_profile(profile_key: str, svc: ConnectionProfileServiceDep):
    return ok(await svc.get_connection_profile(profile_key))


@router.post("/connection-profiles")
async def create_connection_profile(body: ConnectionProfileCreate, svc: ConnectionProfileServiceDep, request: Request):
    result = await svc.create_connection_profile(**body.model_dump(by_alias=False))
    await _refresh_catalog(request)
    return ok(result)


@router.put("/connection-profiles/{profile_key}")
async def update_connection_profile(profile_key: str, body: ConnectionProfileUpdate, svc: ConnectionProfileServiceDep, request: Request):
    result = await svc.update_connection_profile(
        profile_key, **body.model_dump(by_alias=False, exclude_none=True),
    )
    await _refresh_catalog(request)
    return ok(result)


@router.delete("/connection-profiles/{profile_key}")
async def delete_connection_profile(profile_key: str, svc: ConnectionProfileServiceDep, request: Request):
    await svc.delete_connection_profile(profile_key)
    await _refresh_catalog(request)
    return ok(None)


@router.get("/connection-profiles/{profile_key}/provider-models")
async def get_provider_models(profile_key: str, svc: ConnectionProfileServiceDep):
    return ok(await svc.get_provider_models(profile_key))
