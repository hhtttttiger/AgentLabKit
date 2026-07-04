"""DI wiring for files module."""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from common.dependencies import DbSession
from .service import FileService


def get_file_service(db: DbSession) -> FileService:
    return FileService(db)


FileServiceDep = Annotated[FileService, Depends(get_file_service)]
