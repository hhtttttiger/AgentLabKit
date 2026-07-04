"""BackendKnowledgeProvider — 实现 agent_runtime 的 KnowledgeProvider 协议

将 agent_runtime 的 KnowledgeSearchTool 连接到 backend 的 KnowledgeRetrievalService。
支持：
- search(query, top_k) — 全局搜索（无 binding 时的降级方案）
- search_bound_knowledge_bases(...) — 按知识库绑定的作用域搜索
"""

from __future__ import annotations

from typing import Any

from loguru import logger

from agent_runtime.contracts.models import KnowledgeChunk

from .retrieval_service import KnowledgeRetrievalService


class BackendKnowledgeProvider:
    """实现 agent_runtime.tools.registry.KnowledgeProvider 协议

    由 app lifespan 创建并注入到 agent_runtime 的 ToolRegistry 中。
    """

    def __init__(self, retrieval_service: KnowledgeRetrievalService):
        self._retrieval = retrieval_service

    async def search(self, query: str, top_k: int = 5) -> list[KnowledgeChunk]:
        """全局搜索 — 当 agent 没有 knowledge_bindings 时使用

        搜索所有已启用的知识库（后续可加入权限过滤）。
        """
        # 降级：返回空结果，避免搜索所有 KB
        logger.warning("Global knowledge search called without bindings — returning empty")
        return []

    async def search_bound_knowledge_bases(
        self,
        *,
        knowledge_bindings: list[Any],
        query: str,
        top_k: int,
        agent_key: str | None = None,
        agent_version: int | None = None,
    ) -> list[KnowledgeChunk]:
        """作用域搜索 — 只搜索 bindings 中指定的知识库

        参数由 agent_runtime 的 KnowledgeSearchTool 传入：
        - knowledge_bindings: KnowledgeBindingSnapshot 列表
        - query: 用户查询
        - top_k: 返回数量
        """
        kb_ids = [
            b.knowledge_base_id
            for b in knowledge_bindings
            if b.knowledge_base_id
        ]

        if not kb_ids:
            return []

        results = await self._retrieval.asearch_multi(kb_ids, query, top_k)

        return [
            KnowledgeChunk(
                content=r.text,
                title=r.source or None,
                source=r.source or None,
                score=r.score,
                metadata={
                    k: str(v)
                    for k, v in r.metadata.items()
                    if v is not None
                },
            )
            for r in results
        ]
