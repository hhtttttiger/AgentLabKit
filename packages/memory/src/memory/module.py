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
from .providers._common import DummyExtractor


@dataclass(slots=True)
class MemoryModule:
    settings: MemorySettings
    store: MemoryStore
    extractor: MemoryExtractor
    retriever: MemoryRetriever
    injector: MemoryInjector
    consolidator: MemoryConsolidator
    embedding_provider: Any = None


async def create_memory_module(
    *,
    session_factory=None,
    gateway_service=None,
    embedding_provider=None,
    settings: MemorySettings | None = None,
    provider_registry: Any | None = None,
    provider_name: str | None = None,
) -> MemoryModule:
    """工厂函数：创建 MemoryModule 实例。

    Parameters
    ----------
    session_factory:
        async_sessionmaker 实例（provider 模式下可选）。
    gateway_service:
        GatewayService 实例，用于记忆提取 LLM 调用。
    embedding_provider:
        BaseEmbeddingProvider 实例，用于记忆向量化。
        为 None 时使用 _NullEmbeddingProvider 占位（向量搜索返回空）。
    settings:
        可选配置。
    provider_registry:
        MemoryProviderRegistry 实例。传入时使用 provider 模式。
    provider_name:
        要使用的 provider 名称。为 None 时使用默认 provider。
    """
    settings = settings or MemorySettings()

    # Provider 模式：从 registry 获取组件
    if provider_registry is not None:
        provider = provider_registry.get(provider_name or settings.provider)
        # 确保 provider 初始化（验证配置、建立连接等）
        await provider.initialize()
        store = provider.get_store()
        extractor = provider.get_extractor()
        prov_embedding = provider.get_embedding_provider()
        if prov_embedding is not None:
            embedding_provider = prov_embedding
    else:
        # Legacy 模式：直接构建组件
        store = PostgresMemoryStore(session_factory)

        extractor: MemoryExtractor
        if gateway_service is not None:
            extractor = GatewayMemoryExtractor(
                gateway_service=gateway_service,
                model_key=settings.extraction_model,
            )
        else:
            extractor = DummyExtractor()

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
