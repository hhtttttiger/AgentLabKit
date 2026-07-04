from __future__ import annotations

from fastapi import APIRouter, Query

from common.response import ok, paged
from .dependencies import SkillServiceDep
from .schemas import SkillDefCreate, SkillDefUpdate

router = APIRouter()


@router.get("/definitions")
async def list_skill_defs(svc: SkillServiceDep, page: int = Query(1, ge=1), pageSize: int = Query(20, ge=1, le=100), publishedOnly: bool = Query(False)):
    items, total = await svc.list_skill_defs(page=page, page_size=pageSize, published_only=publishedOnly)
    return ok(paged(items, total, page, pageSize))


@router.get("/definitions/{skill_key}")
async def get_skill_def(skill_key: str, svc: SkillServiceDep):
    return ok(await svc.get_skill_def(skill_key))


@router.post("/definitions")
async def create_skill_def(body: SkillDefCreate, svc: SkillServiceDep):
    return ok(await svc.create_skill_def(**body.model_dump()))


@router.put("/definitions/{skill_key}")
async def update_skill_def(skill_key: str, body: SkillDefUpdate, svc: SkillServiceDep):
    return ok(await svc.update_skill_def(skill_key, **body.model_dump(exclude_none=True)))


@router.delete("/definitions/{skill_key}")
async def delete_skill_def(skill_key: str, svc: SkillServiceDep):
    await svc.delete_skill_def(skill_key)
    return ok(None)


@router.post("/definitions/{skill_key}/publish")
async def publish_skill_def(skill_key: str, svc: SkillServiceDep):
    return ok(await svc.publish_skill_def(skill_key))


@router.post("/definitions/{skill_key}/unpublish")
async def unpublish_skill_def(skill_key: str, svc: SkillServiceDep):
    return ok(await svc.unpublish_skill_def(skill_key))
