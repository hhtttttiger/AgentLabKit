"""File storage service — upload, list, get, delete with local filesystem backend."""
from __future__ import annotations

from pathlib import Path

import aiofiles
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from common.errors import NotFoundError
from config import Settings
from .models import StoredFile


class FileService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def upload(
        self,
        *,
        file_name: str,
        content_type: str | None,
        content: bytes,
    ) -> dict:
        settings = Settings()
        base = Path(settings.file_storage_local_base_path)
        base.mkdir(parents=True, exist_ok=True)

        storage_path = str(base / (file_name or "untitled"))

        async with aiofiles.open(storage_path, "wb") as f:
            await f.write(content)

        stored = StoredFile(
            file_name=file_name or "untitled",
            content_type=content_type,
            size_bytes=len(content),
            storage_path=storage_path,
        )
        self._db.add(stored)
        await self._db.flush()
        await self._db.commit()
        return self._to_dict(stored)

    async def list_files(
        self, *, page: int = 1, page_size: int = 20
    ) -> tuple[list[dict], int]:
        query = select(StoredFile).order_by(StoredFile.id.desc())
        total = (
            await self._db.execute(select(func.count()).select_from(StoredFile))
        ).scalar() or 0
        items = (
            await self._db.execute(
                query.offset((page - 1) * page_size).limit(page_size)
            )
        ).scalars().all()
        return [self._to_dict(i) for i in items], total

    async def get_file(self, file_id: int) -> dict:
        f = await self._db.get(StoredFile, file_id)
        if f is None:
            raise NotFoundError("File", str(file_id))
        return self._to_dict(f)

    async def delete_file(self, file_id: int) -> None:
        f = await self._db.get(StoredFile, file_id)
        if f is None:
            raise NotFoundError("File", str(file_id))
        path = Path(f.storage_path)
        if path.exists():
            await aiofiles.os.remove(str(path))
        await self._db.delete(f)
        await self._db.commit()

    @staticmethod
    def _to_dict(f: StoredFile) -> dict:
        return {
            "id": f.id,
            "fileName": f.file_name,
            "contentType": f.content_type,
            "sizeBytes": f.size_bytes,
            "storagePath": f.storage_path,
            "storageType": f.storage_type,
            "createdAtUtc": f.created_at_utc.isoformat() if f.created_at_utc else None,
        }
