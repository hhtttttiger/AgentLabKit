"""MemoryRetriever — 语义搜索 + 时效加权。"""

from __future__ import annotations

from typing import Any

from .contracts import MemoryRecord, MemoryQuery


class MemoryRetriever:
    """检索与当前查询相关的长期记忆。"""

    def __init__(self, store: Any, embedding_provider: Any, settings: Any = None) -> None:
        self._store = store
        self._embedding_provider = embedding_provider
        self._top_k = getattr(settings, "retrieval_top_k", 5) if settings else 5
        self._min_relevance = getattr(settings, "relevance_threshold", 0.5) if settings else 0.5

    async def retrieve(
        self,
        query: str,
        user_id: str,
        *,
        memory_types: list | None = None,
        top_k: int | None = None,
    ) -> list[MemoryRecord]:
        """根据查询文本检索相关记忆。"""
        # 1. 生成 query embedding
        embedding = await self._embedding_provider.aembed(query)

        # 2. 向量搜索
        mem_query = MemoryQuery(
            user_id=user_id,
            query=query,
            memory_types=memory_types,
            top_k=top_k or self._top_k,
            min_relevance=self._min_relevance,
        )
        memories = await self._store.search(mem_query, embedding)
        return memories
