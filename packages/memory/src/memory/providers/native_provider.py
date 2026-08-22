"""NativeMemoryProvider — 包装现有组件的默认 provider。

将 PostgresMemoryStore + GatewayMemoryExtractor + embedding_provider
统一到 MemoryProvider 协议下，实现零改动迁移。
"""

from __future__ import annotations

from typing import Any

from ..store import MemoryStore, PostgresMemoryStore
from ..extractor import MemoryExtractor, GatewayMemoryExtractor
from .base import MemoryProvider


class NativeMemoryProvider:
    """原生 memory provider — 包装现有 Postgres + LLM Gateway 组件。

    这是默认 provider，行为与改造前完全一致。
    """

    name = "native"

    def __init__(
        self,
        *,
        session_factory: Any = None,
        gateway_service: Any = None,
        embedding_provider: Any = None,
        extraction_model: str = "",
        # 也支持直接传入已构建的组件
        store: MemoryStore | None = None,
        extractor: MemoryExtractor | None = None,
    ) -> None:
        if store is not None:
            self._store = store
        elif session_factory is not None:
            self._store = PostgresMemoryStore(session_factory)
        else:
            raise ValueError("Either store or session_factory must be provided")

        if extractor is not None:
            self._extractor = extractor
        elif gateway_service is not None:
            self._extractor = GatewayMemoryExtractor(
                gateway_service=gateway_service,
                model_key=extraction_model,
            )
        else:
            self._extractor = _DummyExtractor()

        self._embedding_provider = embedding_provider

    def get_store(self) -> MemoryStore:
        return self._store

    def get_extractor(self) -> MemoryExtractor:
        return self._extractor

    def get_embedding_provider(self) -> Any | None:
        return self._embedding_provider

    async def initialize(self) -> None:
        """Native provider 无需初始化。"""
        pass

    async def health_check(self) -> bool:
        """Native provider 健康检查 — 尝试执行简单查询。"""
        try:
            await self._store.count_by_type("__health_check__")
            return True
        except Exception:
            return False


class _DummyExtractor:
    """当没有 gateway 时的 fallback extractor。"""

    async def extract_episodic(self, messages: list) -> list[str]:
        return []

    async def extract_semantic(self, messages: list) -> list[str]:
        return []

    async def extract_procedural(self, messages: list) -> list[str]:
        return []
