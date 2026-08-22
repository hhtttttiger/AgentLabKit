"""MemoryProvider 协议定义。

所有 memory provider（native、mem0、zep 等）必须实现此协议。
Provider 统一封装 store + extractor + embedding，对外提供一致接口。
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from ..store import MemoryStore
from ..extractor import MemoryExtractor


@runtime_checkable
class MemoryProvider(Protocol):
    """Memory provider 协议 — 所有 provider 必须实现。

    生命周期：
      1. 通过 ``MemoryProviderRegistry.register()`` 注册实例
      2. 通过 ``get_store()`` / ``get_extractor()`` 获取组件
      3. 由 ``create_memory_module()`` 组装为 MemoryModule
    """

    name: str

    def get_store(self) -> MemoryStore:
        """返回此 provider 的记忆存储实现。"""
        ...

    def get_extractor(self) -> MemoryExtractor:
        """返回此 provider 的记忆提取实现。"""
        ...

    def get_embedding_provider(self) -> Any | None:
        """返回此 provider 的 embedding 实现。None 表示使用默认。"""
        ...

    async def initialize(self) -> None:
        """延迟初始化（创建连接池、验证配置等）。"""
        ...

    async def health_check(self) -> bool:
        """健康检查。"""
        ...
