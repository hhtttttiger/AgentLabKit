"""File storage service — upload, list, get, delete.

组合 BaseFileStorage（磁盘 I/O）+ SQLAlchemy（元数据持久化）。
storage_path 列存储 file_id（由 BaseFileStorage.store() 返回），不存储文件系统路径。
"""
from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import aiofiles
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from common.errors import NotFoundError
from retrieval.providers.file_storage import BaseFileStorage
from .models import StoredFile


class FileService:
    def __init__(
        self,
        db: AsyncSession,
        file_storage: BaseFileStorage | None = None,
        local_base_path: str = "./uploads",
    ) -> None:
        self._db = db
        self._storage = file_storage
        self._local_base = Path(local_base_path)

    async def upload(
        self,
        *,
        file_name: str,
        content_type: str | None,
        content: bytes,
    ) -> dict:
        # 委托 BaseFileStorage 做磁盘写入（UUID 命名防覆盖）
        if self._storage is not None:
            file_id = await self._storage.store(file_name, content, content_type)
        else:
            # 降级：无 storage 时本地写入 + UUID 命名
            file_id = await self._fallback_store(file_name, content)

        stored = StoredFile(
            file_name=file_name or "untitled",
            content_type=content_type,
            size_bytes=len(content),
            storage_path=file_id,  # 存储 file_id，不存储文件系统路径
            storage_type="local",
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

    async def read_content(self, file_id: int) -> bytes:
        """读取文件二进制内容 — 通过 storage 抽象取回。"""
        f = await self._db.get(StoredFile, file_id)
        if f is None:
            raise NotFoundError("File", str(file_id))
        return await self._read_from_storage(f)

    async def download_file(self, file_id: int) -> tuple[bytes, dict]:
        """一次查询同时返回文件内容和元数据。"""
        f = await self._db.get(StoredFile, file_id)
        if f is None:
            raise NotFoundError("File", str(file_id))
        content = await self._read_from_storage(f)
        return content, self._to_dict(f)

    async def _read_from_storage(self, f: StoredFile) -> bytes:
        """从 storage 读取文件内容（内部方法，避免重复查询）。"""
        if self._storage is not None:
            return await self._storage.retrieve(f.storage_path)
        else:
            path = Path(f.storage_path)
            if not path.exists():
                raise FileNotFoundError(f"File on disk not found: {f.storage_path}")
            async with aiofiles.open(path, "rb") as fh:
                return await fh.read()

    async def delete_file(self, file_id: int) -> None:
        f = await self._db.get(StoredFile, file_id)
        if f is None:
            raise NotFoundError("File", str(file_id))

        # 先删 DB 记录，再 best-effort 清理存储
        await self._db.delete(f)
        await self._db.commit()

        if self._storage is not None:
            await self._storage.delete(f.storage_path)
        else:
            path = Path(f.storage_path)
            if path.exists():
                try:
                    await aiofiles.os.remove(str(path))
                except OSError:
                    pass  # best-effort

    @staticmethod
    def _to_dict(f: StoredFile) -> dict:
        return {
            "id": f.id,
            "fileName": f.file_name,
            "contentType": f.content_type,
            "sizeBytes": f.size_bytes,
            "storageType": f.storage_type,
            "createdAtUtc": f.created_at_utc.isoformat() if f.created_at_utc else None,
        }

    async def _fallback_store(self, file_name: str, content: bytes) -> str:
        """无 storage 时的降级存储 — 本地文件系统 + UUID 命名。"""
        self._local_base.mkdir(parents=True, exist_ok=True)
        safe_name = Path(file_name or "untitled").name
        file_id = f"{uuid4().hex[:12]}_{safe_name}"
        storage_path = self._local_base / file_id
        async with aiofiles.open(storage_path, "wb") as f:
            await f.write(content)
        return file_id
