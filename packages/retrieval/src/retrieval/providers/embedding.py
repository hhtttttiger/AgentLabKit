from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from pydantic import BaseModel, Field


class EmbeddingResult(BaseModel):
    """单条 embedding 结果"""
    vector: List[float]
    model: str = ""
    dimensions: int = 0


class BaseEmbeddingProvider(ABC):
    """Embedding 生成抽象基类

    由 backend 通过 llm_gateway 实现，retrieval 包内部不依赖具体 provider。
    """

    @abstractmethod
    async def aembed(self, text: str, **kwargs) -> EmbeddingResult:
        """异步生成单条文本的 embedding"""
        ...

    @abstractmethod
    async def aembed_batch(self, texts: List[str], **kwargs) -> List[EmbeddingResult]:
        """异步批量生成 embedding"""
        ...

    # --- sync 默认实现（子类可覆盖） ---

    def embed(self, text: str, **kwargs) -> EmbeddingResult:
        """同步生成单条 embedding — 默认抛 NotImplementedError，子类按需实现"""
        raise NotImplementedError(
            "Sync embed() is not implemented. Use aembed() or override this method."
        )

    def embed_batch(self, texts: List[str], **kwargs) -> List[EmbeddingResult]:
        """同步批量生成 embedding — 默认抛 NotImplementedError"""
        raise NotImplementedError(
            "Sync embed_batch() is not implemented. Use aembed_batch() or override this method."
        )
