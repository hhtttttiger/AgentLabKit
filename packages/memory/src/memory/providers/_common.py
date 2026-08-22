"""Provider 共享组件 — 避免跨模块重复定义。"""

from __future__ import annotations

from typing import Any


class DummyExtractor:
    """当没有 gateway 时的 fallback extractor。

    所有 extract 方法返回空列表，表示不提取任何记忆。
    用于 NativeMemoryProvider 和 create_memory_module() 的 legacy 模式。
    """

    async def extract_episodic(self, messages: list) -> list[str]:
        return []

    async def extract_semantic(self, messages: list) -> list[str]:
        return []

    async def extract_procedural(self, messages: list) -> list[str]:
        return []
