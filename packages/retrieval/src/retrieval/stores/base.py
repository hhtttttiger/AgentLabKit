from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class VectorRecord(BaseModel):
    """待写入向量存储的记录"""
    id: str
    vector: List[float]
    metadata: Dict = Field(default_factory=dict)


class VectorSearchResult(BaseModel):
    """向量检索结果"""
    id: str
    score: float
    metadata: Dict = Field(default_factory=dict)


class BaseVectorStore(ABC):
    """向量存储抽象基类

    collection 语义上对应一个知识库（kb_id），
    由 backend 通过 pgvector 等实现。
    """

    @abstractmethod
    async def aupsert(self, collection: str, records: List[VectorRecord], session=None) -> None:
        """异步写入 / 更新向量记录

        Args:
            session: 可选的外部 SQLAlchemy AsyncSession。传入时复用该 session
                     的事务，调用方负责 commit；未传入时自管 session 和 commit。
        """
        ...

    @abstractmethod
    async def aquery(
        self,
        collection: str,
        vector: List[float],
        top_k: int = 5,
        filters: Optional[Dict] = None,
    ) -> List[VectorSearchResult]:
        """异步向量相似度检索"""
        ...

    @abstractmethod
    async def adelete(self, collection: str, ids: List[str]) -> None:
        """异步删除向量记录"""
        ...

    async def adelete_by_document(self, collection: str, document_id: str) -> None:
        """按文档 ID 删除所有关联向量（幂等 re-index 用）

        默认 no-op，由具体 store 按需实现。
        """
        ...

    async def aquery_fulltext(
        self,
        collection: str,
        query_text: str,
        top_k: int = 10,
        filters: Optional[Dict] = None,
    ) -> List[VectorSearchResult]:
        """全文检索（pg_trgm 等）

        默认 no-op，由具体 store 按需实现。
        """
        return []
