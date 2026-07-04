from __future__ import annotations

from fastapi import APIRouter, Query, Request

from common.response import ok, paged
from .dependencies import ToolServiceDep
from .schemas import ToolDefCreate, ToolDefUpdate

router = APIRouter()


@router.post("/definitions/sync")
async def sync_builtin_tools(request: Request, svc: ToolServiceDep):
    runtime = getattr(request.app.state, "agent_runtime", None)
    if runtime is None or not hasattr(runtime, "tool_registry"):
        from common.errors import AppError
        raise AppError("agent_runtime_catalog_unreachable", status_code=503)

    specs = [
        {
            "name": spec.name,
            "description": spec.description,
            "parameters_schema": spec.parameters_schema,
            "label": spec.label,
        }
        for spec in runtime.tool_registry.dynamic_registry.list_all()
    ]
    count = await svc.sync_builtin_tools(specs)
    return ok({"synced": count})


@router.get("/definitions")
async def list_tool_defs(
    svc: ToolServiceDep,
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    sourceType: str | None = Query(None),
    status: str | None = Query(None),
    search: str | None = Query(None),
):
    items, total = await svc.list_tool_defs(page=page, page_size=pageSize, source_type=sourceType, status=status, search=search)
    return ok(paged(items, total, page, pageSize))


@router.get("/definitions/{tool_name}")
async def get_tool_def(tool_name: str, svc: ToolServiceDep):
    return ok(await svc.get_tool_def(tool_name))


@router.post("/definitions")
async def create_tool_def(body: ToolDefCreate, svc: ToolServiceDep):
    return ok(await svc.create_tool_def(**body.model_dump(by_alias=False)))


@router.put("/definitions/{tool_name}")
async def update_tool_def(tool_name: str, body: ToolDefUpdate, svc: ToolServiceDep):
    return ok(await svc.update_tool_def(tool_name, **body.model_dump(by_alias=False, exclude_none=True)))


@router.post("/definitions/{tool_name}/disable")
async def disable_tool_def(tool_name: str, svc: ToolServiceDep):
    return ok(await svc.disable_tool_def(tool_name))
