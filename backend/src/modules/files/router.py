from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, Query, UploadFile, File as FastAPIFile
from fastapi.responses import Response

from common.errors import NotFoundError
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


@router.get("/{file_id}/content")
async def download_file(file_id: int, svc: FileServiceDep):
    """下载文件二进制内容。"""
    try:
        content, file_meta = await svc.download_file(file_id)
    except FileNotFoundError:
        raise NotFoundError("FileContent", str(file_id))

    safe_name = file_meta.get("fileName", "download")
    # RFC 5987: filename*=UTF-8''<encoded> 防 header 注入
    encoded_name = quote(safe_name, safe="")

    return Response(
        content=content,
        media_type=file_meta.get("contentType") or "application/octet-stream",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_name}",
        },
    )


@router.delete("/{file_id}")
async def delete_file(file_id: int, svc: FileServiceDep):
    await svc.delete_file(file_id)
    return ok(None)
