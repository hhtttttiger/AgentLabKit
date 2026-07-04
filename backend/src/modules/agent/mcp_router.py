from __future__ import annotations

from fastapi import APIRouter, Query

from common.response import ok, paged
from .dependencies import McpServiceDep
from .schemas import McpConfigCreate, McpConfigUpdate

router = APIRouter()


@router.get("/servers")
async def list_mcp_servers(svc: McpServiceDep, page: int = Query(1, ge=1), pageSize: int = Query(200, ge=1, le=500)):
    items, total = await svc.list_mcp_servers(page=page, page_size=pageSize)
    return ok(paged(items, total, page, pageSize))


@router.get("/servers/{name}")
async def get_mcp_server(name: str, svc: McpServiceDep):
    return ok(await svc.get_mcp_server(name))


@router.post("/servers")
async def create_mcp_server(body: McpConfigCreate, svc: McpServiceDep):
    return ok(await svc.create_mcp_server(**body.model_dump(by_alias=False)))


@router.put("/servers/{name}")
async def update_mcp_server(name: str, body: McpConfigUpdate, svc: McpServiceDep):
    return ok(await svc.update_mcp_server(name, **body.model_dump(by_alias=False, exclude_none=True)))


@router.delete("/servers/{name}")
async def delete_mcp_server(name: str, svc: McpServiceDep):
    await svc.delete_mcp_server(name)
    return ok(None)
