"""DI wiring for files module."""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from common.dependencies import DbSession
from .service import FileService


def get_file_service(db: DbSession, request: Request) -> FileService:
    file_storage = getattr(request.app.state, "file_storage", None)
    settings = request.app.state.settings
    return FileService(db, file_storage=file_storage, local_base_path=settings.file_storage_local_base_path)


FileServiceDep = Annotated[FileService, Depends(get_file_service)]
