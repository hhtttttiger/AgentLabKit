"""LocalFileStorage — 基于本地文件系统的 BaseFileStorage 实现。

只负责磁盘 I/O，不依赖 DB session。适合被 processing 等进程级组件使用。
FileService 在其上层组合 DB 元数据管理。
"""
from __future__ import annotations

import re
from pathlib import Path
from uuid import uuid4

import aiofiles

from retrieval.providers.file_storage import BaseFileStorage

# 文件名白名单：只保留字母、数字、点、下划线、连字符
_SAFE_NAME_RE = re.compile(r"[^\w.\-]")


def _sanitize_file_name(file_name: str) -> str:
    """清理文件名，防止路径穿越和特殊字符。"""
    name = file_name or "untitled"
    # 取 basename（防路径穿越）
    name = Path(name).name
    # 替换不安全字符
    name = _SAFE_NAME_RE.sub("_", name)
    # 防空文件名
    return name or "untitled"


class LocalFileStorage(BaseFileStorage):
    """本地文件系统存储 — UUID 命名防覆盖，flat 目录结构。"""

    def __init__(self, base_path: str) -> None:
        self._base = Path(base_path)
        self._base.mkdir(parents=True, exist_ok=True)

    async def store(
        self,
        file_name: str,
        content: bytes,
        content_type: str | None = None,
    ) -> str:
        safe_name = _sanitize_file_name(file_name)
        file_id = f"{uuid4().hex[:12]}_{safe_name}"
        storage_path = self._base / file_id

        async with aiofiles.open(storage_path, "wb") as f:
            await f.write(content)

        return file_id

    async def retrieve(self, file_id: str) -> bytes:
        storage_path = self._base / file_id
        if not storage_path.exists():
            raise FileNotFoundError(f"File not found: {file_id}")

        async with aiofiles.open(storage_path, "rb") as f:
            return await f.read()

    async def delete(self, file_id: str) -> bool:
        storage_path = self._base / file_id
        if not storage_path.exists():
            return False

        await aiofiles.os.remove(str(storage_path))
        return True
