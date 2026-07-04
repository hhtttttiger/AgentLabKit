"""Glossary API Router — 纯 HTTP 协议处理层。

所有业务逻辑委托给 GlossaryService。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File as FastAPIFile, Query, UploadFile

from common.dependencies import DbSession
from common.response import ok
from .dependencies import get_glossary_service
from .schemas import (
    CategoryCreateRequest,
    CategoryUpdateRequest,
    TermCreateRequest,
    TermUpdateRequest,
)
from .services.glossary_service import GlossaryService

router = APIRouter()


# ── Categories ──────────────────────────────────────────────────

@router.get("/categories")
async def list_categories(
    svc: GlossaryService = Depends(get_glossary_service),
    page: int = Query(1, ge=1),
    pageSize: int = Query(12, ge=1, le=200),
    search: str | None = None,
):
    items, total = await svc.list_categories(page=page, page_size=pageSize, search=search)
    return ok({
        "items": [i.model_dump(by_alias=True) for i in items],
        "page": page,
        "pageSize": pageSize,
        "totalCount": total,
    })


@router.get("/categories/{category_id}")
async def get_category(category_id: int, svc: GlossaryService = Depends(get_glossary_service)):
    return ok((await svc.get_category(category_id)).model_dump(by_alias=True))


@router.post("/categories")
async def create_category(
    body: CategoryCreateRequest,
    svc: GlossaryService = Depends(get_glossary_service),
):
    return ok((await svc.create_category(body)).model_dump(by_alias=True))


@router.put("/categories/{category_id}")
async def update_category(
    category_id: int,
    body: CategoryUpdateRequest,
    svc: GlossaryService = Depends(get_glossary_service),
):
    return ok((await svc.update_category(category_id, body)).model_dump(by_alias=True))


@router.delete("/categories/{category_id}")
async def delete_category(category_id: int, svc: GlossaryService = Depends(get_glossary_service)):
    await svc.delete_category(category_id)
    return ok(None)


# ── Terms ───────────────────────────────────────────────────────

@router.get("/terms")
async def list_terms(
    svc: GlossaryService = Depends(get_glossary_service),
    categoryId: int | None = None,
    page: int = Query(1, ge=1),
    pageSize: int = Query(10, ge=1, le=200),
    search: str | None = None,
):
    items, total = await svc.list_terms(
        category_id=categoryId, page=page, page_size=pageSize, search=search,
    )
    return ok({
        "items": [i.model_dump(by_alias=True) for i in items],
        "page": page,
        "pageSize": pageSize,
        "totalCount": total,
    })


@router.get("/terms/{term_id}")
async def get_term(term_id: int, svc: GlossaryService = Depends(get_glossary_service)):
    return ok((await svc.get_term(term_id)).model_dump(by_alias=True))


@router.post("/terms")
async def create_term(
    body: TermCreateRequest,
    svc: GlossaryService = Depends(get_glossary_service),
):
    return ok((await svc.create_term(body)).model_dump(by_alias=True))


@router.put("/terms/{term_id}")
async def update_term(
    term_id: int,
    body: TermUpdateRequest,
    svc: GlossaryService = Depends(get_glossary_service),
):
    return ok((await svc.update_term(term_id, body)).model_dump(by_alias=True))


@router.delete("/terms/{term_id}")
async def delete_term(term_id: int, svc: GlossaryService = Depends(get_glossary_service)):
    await svc.delete_term(term_id)
    return ok(None)


@router.post("/terms/import")
async def import_terms(
    svc: GlossaryService = Depends(get_glossary_service),
    file: UploadFile = FastAPIFile(...),
):
    """批量导入术语（CSV：列 term, synonyms, category；synonyms 以 | 分隔）。"""
    content = await file.read()
    result = await svc.import_terms(content, file.filename or "")
    return ok(result)
