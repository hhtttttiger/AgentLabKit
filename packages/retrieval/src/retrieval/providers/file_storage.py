"""文件存储抽象基类 — 定义知识库模块与文件存储之间的契约。

由 backend 的 LocalFileStorage 实现，retrieval 包内部不依赖具体存储后端。
"""
from __future__ import annotations

from abc import ABC, abstractmethod


class BaseFileStorage(ABC):
    """文件存储抽象 — 支持文件的存、取、删。

    实现方只需关注磁盘/S3 等存储介质，不涉及 DB 元数据。
    """

    @abstractmethod
    async def store(
        self,
        file_name: str,
        content: bytes,
        content_type: str | None = None,
    ) -> str:
        """存储文件，返回 file_id（供后续 retrieve / delete 使用）。

        :param file_name: 原始文件名（用于扩展名推断，不保证唯一）
        :param content: 文件二进制内容
        :param content_type: MIME 类型（可选）
        :return: 唯一 file_id
        """
        ...

    @abstractmethod
    async def retrieve(self, file_id: str) -> bytes:
        """取回文件内容。

        :param file_id: store() 返回的 file_id
        :return: 文件二进制内容
        :raises FileNotFoundError: file_id 不存在
        """
        ...

    @abstractmethod
    async def delete(self, file_id: str) -> bool:
        """删除文件。

        :param file_id: store() 返回的 file_id
        :return: 是否成功删除（file_id 不存在时返回 False）
        """
        ...
