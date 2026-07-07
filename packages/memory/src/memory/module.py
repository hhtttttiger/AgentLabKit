"""MemoryModule — 遵循项目统一的 Module 模式。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .config import MemorySettings
from .store import MemoryStore, PostgresMemoryStore
from .extractor import MemoryExtractor, GatewayMemoryExtractor
from .retrieval import MemoryRetriever
from .injector import MemoryInjector
from .consolidator import MemoryConsolidator


@dataclass(slots=True)
class MemoryModule:
    settings: MemorySettings
    store: MemoryStore
    extractor: MemoryExtractor
    retriever: MemoryRetriever
    injector: MemoryInjector
    consolidator: MemoryConsolidator
    embedding_provider: Any = None


def create_memory_module(
    *,
    session_factory,
    gateway_service=None,
    embedding_provider=None,
    settings: MemorySettings | None = None,
) -> MemoryModule:
    """工厂函数：创建 MemoryModule 实例。

    Parameters
    ----------
    session_factory:
        async_sessionmaker 实例。
    gateway_service:
        GatewayService 实例，用于记忆提取 LLM 调用。
    embedding_provider:
        BaseEmbeddingProvider 实例，用于记忆向量化。
        为 None 时使用 _NullEmbeddingProvider 占位（向量搜索返回空）。
    settings:
        可选配置。
    """
    settings = settings or MemorySettings()
    store = PostgresMemoryStore(session_factory)

    extractor: MemoryExtractor
    if gateway_service is not None:
        extractor = GatewayMemoryExtractor(
            gateway_service=gateway_service,
            model_key=settings.extraction_model,
        )
    else:
        extractor = _DummyExtractor()

    if embedding_provider is None:
        embedding_provider = _NullEmbeddingProvider()

    retriever = MemoryRetriever(
        store=store,
        embedding_provider=embedding_provider,
        settings=settings,
    )
    injector = MemoryInjector()
    consolidator = MemoryConsolidator(store=store, extractor=extractor)

    return MemoryModule(
        settings=settings,
        store=store,
        extractor=extractor,
        retriever=retriever,
        injector=injector,
        consolidator=consolidator,
        embedding_provider=embedding_provider,
    )


class _NullEmbeddingProvider:
    """占位 embedding provider —— 返回零向量（维度 1024）。

    pgvector 需要合法的向量格式，空列表会导致 SQL 报错。
    零向量与任何向量的余弦距离为 0，会被 relevance_threshold 过滤掉。
    """

    _DIM = 1024

    async def aembed(self, text: str) -> list[float]:
        return [0.0] * self._DIM


class _DummyExtractor:
    """当没有 gateway 时的 fallback extractor。"""

    async def extract_episodic(self, messages: list) -> list[str]:
        return []

    async def extract_semantic(self, messages: list) -> list[str]:
        return []

    async def extract_procedural(self, messages: list) -> list[str]:
        return []
