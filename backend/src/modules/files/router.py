from __future__ import annotations

from fastapi import APIRouter, Query, UploadFile, File as FastAPIFile

from common.response import ok, paged
from .dependencies import FileServiceDep

router = APIRouter()


@router.post("")
async def upload_file(file: UploadFile = FastAPIFile(...), svc: FileServiceDep = ...):
    content = await file.read()
    result = await svc.upload(
        file_name=file.filename or "untitled",
        content_type=file.content_type,
        content=content,
    )
    return ok(result)


@router.get("")
async def list_files(
    svc: FileServiceDep,
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
):
    items, total = await svc.list_files(page=page, page_size=pageSize)
    return ok(paged(items, total, page, pageSize))


@router.get("/{file_id}")
async def get_file(file_id: int, svc: FileServiceDep):
    return ok(await svc.get_file(file_id))


@router.delete("/{file_id}")
async def delete_file(file_id: int, svc: FileServiceDep):
    await svc.delete_file(file_id)
    return ok(None)
