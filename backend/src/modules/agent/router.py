from __future__ import annotations

from fastapi import APIRouter, Query

from common.response import ok, paged
from .dependencies import AgentServiceDep
from .schemas import AgentCreate, AgentUpdate, VersionCreate, ToolBindingCreate, KbBindingCreate, PublishAgentRequest, DisableAgentRequest

router = APIRouter()


# ── Agent CRUD ──────────────────────────────────────────────────

@router.get("/options")
async def list_agent_options(svc: AgentServiceDep):
    """下拉列表选项 — 仅返回 value/label。"""
    options = await svc.list_options()
    return ok(options)


@router.get("")
async def list_agents(svc: AgentServiceDep, page: int = Query(1, ge=1), pageSize: int = Query(20, ge=1, le=100), status: str | None = Query(None)):
    items, total = await svc.list_agents(page=page, page_size=pageSize, status=status)
    return ok(paged(items, total, page, pageSize))


@router.post("")
async def create_agent(body: AgentCreate, svc: AgentServiceDep):
    return ok(await svc.create_agent(**body.model_dump(by_alias=False)))


@router.get("/{agent_key}")
async def get_agent(agent_key: str, svc: AgentServiceDep):
    return ok(await svc.get_agent(agent_key))


@router.put("/{agent_key}")
async def update_agent(agent_key: str, body: AgentUpdate, svc: AgentServiceDep):
    return ok(await svc.update_agent(agent_key, **body.model_dump(by_alias=False, exclude_none=True)))


@router.delete("/{agent_key}")
async def delete_agent(agent_key: str, svc: AgentServiceDep):
    await svc.delete_agent(agent_key)
    return ok(None)


# ── Versions ────────────────────────────────────────────────────

@router.get("/{agent_key}/versions")
async def list_versions(agent_key: str, svc: AgentServiceDep, page: int = Query(1, ge=1), pageSize: int = Query(20, ge=1, le=100)):
    items, total = await svc.list_versions(agent_key, page=page, page_size=pageSize)
    return ok(paged(items, total, page, pageSize))


@router.post("/{agent_key}/versions")
async def create_version(agent_key: str, body: VersionCreate, svc: AgentServiceDep):
    return ok(await svc.create_version(agent_key, body))


@router.get("/{agent_key}/versions/{version_number}")
async def get_version(agent_key: str, version_number: int, svc: AgentServiceDep):
    return ok(await svc.get_version(agent_key, version_number))


@router.put("/{agent_key}/versions/{version_number}")
async def update_version(agent_key: str, version_number: int, body: VersionCreate, svc: AgentServiceDep):
    return ok(await svc.update_version(agent_key, version_number, body))


# ── Publish / Disable ───────────────────────────────────────────

@router.post("/{agent_key}/publish")
async def publish_agent(agent_key: str, body: PublishAgentRequest, svc: AgentServiceDep):
    return ok(await svc.publish_agent(agent_key, body.version_number))


@router.post("/{agent_key}/disable")
async def disable_agent(agent_key: str, body: DisableAgentRequest, svc: AgentServiceDep):
    return ok(await svc.disable_agent(agent_key))


# ── Audits ──────────────────────────────────────────────────────

@router.get("/{agent_key}/audits")
async def list_audits(agent_key: str, svc: AgentServiceDep, page: int = Query(1, ge=1), pageSize: int = Query(20, ge=1, le=100)):
    items, total = await svc.list_audits(agent_key, page=page, page_size=pageSize)
    return ok(paged(items, total, page, pageSize))


@router.get("/{agent_key}/audits/{run_id}")
async def get_audit(agent_key: str, run_id: str, svc: AgentServiceDep):
    return ok(await svc.get_audit(agent_key, run_id))


# ── Tool Bindings (per version) ─────────────────────────────────

@router.get("/{agent_key}/versions/{version_number}/tool-bindings")
async def list_tool_bindings(agent_key: str, version_number: int, svc: AgentServiceDep):
    return ok(await svc.list_tool_bindings(agent_key, version_number))


@router.post("/{agent_key}/versions/{version_number}/tool-bindings")
async def create_tool_binding(agent_key: str, version_number: int, body: ToolBindingCreate, svc: AgentServiceDep):
    return ok(await svc.create_tool_binding(agent_key, version_number, **body.model_dump(by_alias=False)))


# ── KB Bindings (per version) ───────────────────────────────────

@router.get("/{agent_key}/versions/{version_number}/knowledge-base-bindings")
async def list_kb_bindings(agent_key: str, version_number: int, svc: AgentServiceDep):
    return ok(await svc.list_kb_bindings(agent_key, version_number))


@router.post("/{agent_key}/versions/{version_number}/knowledge-base-bindings")
async def create_kb_binding(agent_key: str, version_number: int, body: KbBindingCreate, svc: AgentServiceDep):
    return ok(await svc.create_kb_binding(agent_key, version_number, **body.model_dump(by_alias=False)))
