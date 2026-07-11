"""GatewayEmbeddingProvider — 通过 llm_gateway 生成 embedding 向量"""

from __future__ import annotations

import asyncio
from typing import List

from loguru import logger

from retrieval.providers.embedding import BaseEmbeddingProvider, EmbeddingResult

# llm_gateway 的类型仅在运行时导入
from llm_gateway.models import EmbeddingGenerateRequest
from llm_gateway import GatewayProtocol


class GatewayEmbeddingProvider(BaseEmbeddingProvider):
    """调用 llm_gateway 的 generate_embedding API 生成 embedding 向量

    用于 backend 的 KnowledgeRetrievalService 中，
    对文档分段和查询进行向量化。
    """

    def __init__(
        self,
        gateway: GatewayProtocol,
        model: str = "text-embedding-3-small",
        dimensions: int = 1024,
        batch_size: int = 20,
    ):
        self._gateway = gateway
        self._model = model
        self._dimensions = dimensions
        self._batch_size = batch_size

    async def aembed(self, text: str, **kwargs) -> EmbeddingResult:
        model = kwargs.get("model", self._model)
        dimensions = kwargs.get("dimensions", self._dimensions)
        resp = await self._gateway.generate_embedding(
            EmbeddingGenerateRequest(model=model, input=text, dimensions=dimensions)
        )
        return EmbeddingResult(
            vector=resp.embedding,
            model=resp.model,
            dimensions=resp.dimensions,
        )

    async def aembed_batch(self, texts: List[str], **kwargs) -> List[EmbeddingResult]:
        """逐批调用 gateway 的 embedding 接口

        gateway 当前只支持单条输入，因此按 batch_size 分组并发调用。
        """
        results: List[EmbeddingResult] = []
        for i in range(0, len(texts), self._batch_size):
            batch = texts[i : i + self._batch_size]
            tasks = [self.aembed(t, **kwargs) for t in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            for j, r in enumerate(batch_results):
                if isinstance(r, Exception):
                    logger.error(f"Embedding failed for batch item {i + j}: {r}")
                    results.append(
                        EmbeddingResult(vector=[], model=self._model, dimensions=0)
                    )
                else:
                    results.append(r)
        return results
