"""Knowledge Base API Router — 纯 HTTP 协议处理层。

所有业务逻辑委托给 service 层：
- KnowledgeBaseService → KB + 文件夹 CRUD
- DocumentService → 文档 CRUD + 处理编排
- SearchService → 搜索（委托 retrieval 包）
"""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, Query, UploadFile, File as FastAPIFile

from common.dependencies import DbSession
from common.response import ok, paged
from .dependencies import get_kb_service, get_document_service, get_search_service
from .schemas import (
    KbCreateRequest,
    KbUpdateRequest,
    FolderCreateRequest,
    FolderUpdateRequest,
    FolderMoveRequest,
    QaCreateRequest,
    QaUpdateRequest,
    DocumentMoveRequest,
    SearchRequest,
)

router = APIRouter()


# ── Knowledge Base CRUD ─────────────────────────────────────────

@router.get("")
async def list_kbs(
    db: DbSession,
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    keyword: str | None = None,
    status: str | None = None,
    svc=Depends(get_kb_service),
):
    items, total = await svc.list_kbs(page, pageSize, keyword, status)
    return ok(paged([i.model_dump(by_alias=True) for i in items], total, page, pageSize))


@router.post("")
async def create_kb(body: KbCreateRequest, db: DbSession, svc=Depends(get_kb_service)):
    view = await svc.create_kb(body)
    return ok(view.model_dump(by_alias=True))


@router.get("/{kb_id}")
async def get_kb(kb_id: int, db: DbSession, svc=Depends(get_kb_service)):
    return ok((await svc.get_kb(kb_id)).model_dump(by_alias=True))


@router.put("/{kb_id}")
async def update_kb(kb_id: int, body: KbUpdateRequest, db: DbSession, svc=Depends(get_kb_service)):
    return ok((await svc.update_kb(kb_id, body)).model_dump(by_alias=True))


@router.delete("/{kb_id}")
async def delete_kb(kb_id: int, db: DbSession, svc=Depends(get_kb_service)):
    await svc.delete_kb(kb_id)
    return ok(None)


# ── Folders ─────────────────────────────────────────────────────

@router.get("/{kb_id}/folders")
async def list_folders(kb_id: int, db: DbSession, svc=Depends(get_kb_service)):
    folders = await svc.list_folders(kb_id)
    return ok([f.model_dump(by_alias=True) for f in folders])


@router.post("/{kb_id}/folders")
async def create_folder(kb_id: int, body: FolderCreateRequest, db: DbSession, svc=Depends(get_kb_service)):
    return ok((await svc.create_folder(kb_id, body)).model_dump(by_alias=True))


@router.patch("/{kb_id}/folders/{folder_id}")
async def update_folder(
    kb_id: int, folder_id: int, body: FolderUpdateRequest,
    db: DbSession, svc=Depends(get_kb_service),
):
    return ok((await svc.update_folder(kb_id, folder_id, body)).model_dump(by_alias=True))


@router.delete("/{kb_id}/folders/{folder_id}")
async def delete_folder(kb_id: int, folder_id: int, db: DbSession, svc=Depends(get_kb_service)):
    await svc.delete_folder(kb_id, folder_id)
    return ok(None)


@router.post("/{kb_id}/folders/{folder_id}/move")
async def move_folder(
    kb_id: int, folder_id: int, body: FolderMoveRequest,
    db: DbSession, svc=Depends(get_kb_service),
):
    target_id = int(body.target_parent_folder_id) if body.target_parent_folder_id else None
    await svc.move_folder(kb_id, folder_id, target_id)
    return ok(None)


# ── Documents ───────────────────────────────────────────────────

@router.get("/{kb_id}/documents")
async def list_documents(
    kb_id: int, db: DbSession,
    page: int = Query(1, ge=1), pageSize: int = Query(20, ge=1, le=100),
    folder_id: int | None = None,
    source_type: str | None = None,
    svc=Depends(get_document_service),
):
    items, total = await svc.list_documents(kb_id, page, pageSize, folder_id, source_type)
    return ok(paged([i.model_dump(by_alias=True) for i in items], total, page, pageSize))


@router.get("/{kb_id}/documents/top-recalled")
async def list_top_recalled_documents(
    kb_id: int, db: DbSession,
    limit: int = Query(100, ge=1, le=500),
    svc=Depends(get_document_service),
):
    """被召回次数最多的文档榜单。

    必须注册在 `/{kb_id}/documents/{doc_id}` 之前——FastAPI 按注册顺序匹配路由，
    否则 `top-recalled` 会被 `{doc_id}: int` 路径参数捕获并返回 422。
    """
    items = await svc.list_top_recalled_documents(kb_id, limit)
    return ok([i.model_dump(by_alias=True) for i in items])


@router.post("/{kb_id}/documents/upload")
async def upload_document(
    kb_id: int,
    background_tasks: BackgroundTasks,
    db: DbSession,
    file: UploadFile = FastAPIFile(...),
    folder_id: int | None = None,
    svc=Depends(get_document_service),
):
    content = await file.read()
    view = await svc.upload_document(
        kb_id=kb_id,
        file_content=content,
        file_name=file.filename or "untitled",
        content_type=file.content_type,
        file_size=len(content),
        folder_id=folder_id,
        background_tasks=background_tasks,
    )
    return ok(view.model_dump(by_alias=True))


@router.post("/{kb_id}/documents/qa")
async def create_qa_document(
    kb_id: int,
    body: QaCreateRequest,
    background_tasks: BackgroundTasks,
    db: DbSession,
    svc=Depends(get_document_service),
):
    view = await svc.create_qa(kb_id, body, background_tasks)
    return ok(view.model_dump(by_alias=True))


@router.post("/{kb_id}/documents/qa/import")
async def import_qa_documents(
    kb_id: int,
    background_tasks: BackgroundTasks,
    db: DbSession,
    file: UploadFile = FastAPIFile(...),
    svc=Depends(get_document_service),
):
    """批量导入 QA 对（CSV/JSON 文件）。"""
    import json

    content = await file.read()
    filename = file.filename or ""

    qa_pairs: list[dict] = []
    if filename.endswith(".json"):
        qa_pairs = json.loads(content)
    elif filename.endswith(".csv"):
        import csv
        import io
        reader = csv.DictReader(io.StringIO(content.decode("utf-8")))
        qa_pairs = [row for row in reader if row.get("question") and row.get("answer")]
    else:
        # 尝试 JSON 格式
        qa_pairs = json.loads(content)

    result = await svc.bulk_import_qa(kb_id, qa_pairs, background_tasks)
    return ok(result.model_dump(by_alias=True))


@router.get("/{kb_id}/documents/{doc_id}")
async def get_document(kb_id: int, doc_id: int, db: DbSession, svc=Depends(get_document_service)):
    return ok((await svc.get_document(kb_id, doc_id)).model_dump(by_alias=True))


@router.put("/{kb_id}/documents/{doc_id}")
async def update_document(
    kb_id: int, doc_id: int, body: QaUpdateRequest,
    db: DbSession, svc=Depends(get_document_service),
):
    return ok((await svc.update_qa(kb_id, doc_id, body)).model_dump(by_alias=True))


@router.delete("/{kb_id}/documents/{doc_id}")
async def delete_document(kb_id: int, doc_id: int, db: DbSession, svc=Depends(get_document_service)):
    await svc.delete_document(kb_id, doc_id)
    return ok(None)


@router.post("/{kb_id}/documents/{doc_id}/move")
async def move_document(
    kb_id: int, doc_id: int, body: DocumentMoveRequest,
    db: DbSession, svc=Depends(get_document_service),
):
    target_id = int(body.target_folder_id) if body.target_folder_id else None
    await svc.move_document(kb_id, doc_id, target_id)
    return ok(None)


@router.post("/{kb_id}/documents/{doc_id}/reindex")
async def reindex_document(
    kb_id: int, doc_id: int,
    background_tasks: BackgroundTasks,
    db: DbSession,
    svc=Depends(get_document_service),
):
    await svc.reindex_document(kb_id, doc_id, background_tasks)
    return ok(None)


@router.get("/{kb_id}/documents/{doc_id}/processing")
async def get_document_processing(kb_id: int, doc_id: int, db: DbSession, svc=Depends(get_document_service)):
    job = await svc.get_document_processing(kb_id, doc_id)
    return ok(job.model_dump(by_alias=True) if job else None)


@router.get("/{kb_id}/documents/{doc_id}/indexes")
async def list_document_indexes(kb_id: int, doc_id: int, db: DbSession, svc=Depends(get_document_service)):
    indexes = await svc.list_document_indexes(kb_id, doc_id)
    return ok([i.model_dump(by_alias=True) for i in indexes])


# ── Segments ────────────────────────────────────────────────────

@router.get("/{kb_id}/documents/{doc_id}/segments")
async def list_segments(
    kb_id: int, doc_id: int, db: DbSession,
    page: int = Query(1, ge=1), pageSize: int = Query(50, ge=1, le=200),
    svc=Depends(get_document_service),
):
    items, total = await svc.list_segments(kb_id, doc_id, page, pageSize)
    return ok(paged([i.model_dump(by_alias=True) for i in items], total, page, pageSize))


@router.get("/{kb_id}/documents/{doc_id}/segments/{seg_id}")
async def get_segment(kb_id: int, doc_id: int, seg_id: int, db: DbSession, svc=Depends(get_document_service)):
    return ok((await svc.get_segment(kb_id, doc_id, seg_id)).model_dump(by_alias=True))


# ── Processing Jobs ─────────────────────────────────────────────

@router.get("/{kb_id}/processing/jobs")
async def list_processing_jobs(kb_id: int, db: DbSession, svc=Depends(get_document_service)):
    jobs = await svc.list_processing_jobs(kb_id)
    return ok([j.model_dump(by_alias=True) for j in jobs])


# ── Glossary Binding ────────────────────────────────────────────

@router.get("/{kb_id}/glossary/categories")
async def get_kb_glossary_categories(kb_id: int, db: DbSession):
    from modules.glossary.services.glossary_service import GlossaryService
    svc = GlossaryService(db)
    view = await svc.get_kb_glossary_binding(kb_id)
    return ok(view.model_dump(by_alias=True))


@router.put("/{kb_id}/glossary/categories")
async def replace_kb_glossary_categories(kb_id: int, body: dict, db: DbSession):
    from modules.glossary.services.glossary_service import GlossaryService
    svc = GlossaryService(db)
    category_ids: list[int] = body.get("categoryIds", [])
    await svc.replace_kb_glossary_binding(kb_id, category_ids)
    return ok(None)


# ── Search ──────────────────────────────────────────────────────

@router.post("/{kb_id}/search")
async def search_kb(kb_id: int, body: SearchRequest, db: DbSession, svc=Depends(get_search_service)):
    response = await svc.search(kb_id, body)
    return ok(response.model_dump(by_alias=True))
