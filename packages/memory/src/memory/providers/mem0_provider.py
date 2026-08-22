"""Mem0MemoryProvider — 适配 Mem0 开源记忆库。

Mem0 内置记忆提取、去重、合并，因此 extractor 为 no-op。
记忆类型通过 metadata 存储，检索时按类型过滤。

依赖：pip install mem0ai
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from ..contracts import MemoryRecord, MemoryType, MemoryQuery
from ..store import MemoryStore
from ..extractor import MemoryExtractor
from .base import MemoryProvider

logger = logging.getLogger(__name__)


class Mem0MemoryProvider:
    """Mem0 memory provider — 适配 Mem0 开源库。

    Mem0 自动处理记忆提取、去重和合并，
    因此 extractor 是 no-op（Mem0 在 add 时自动提取）。
    """

    name = "mem0"

    def __init__(
        self,
        *,
        config: dict[str, Any] | None = None,
        api_key: str | None = None,
    ) -> None:
        """初始化 Mem0 provider。

        Args:
            config: Mem0 配置字典（传给 Memory.from_config）。
                   为 None 时使用默认配置。
            api_key: OpenAI API key（Mem0 需要 LLM 做提取）。
                    也可通过环境变量 OPENAI_API_KEY 设置。
        """
        self._config = config or {}
        self._api_key = api_key
        self._client = None  # 延迟初始化

    async def initialize(self) -> None:
        """延迟初始化 Mem0 客户端。"""
        if self._client is not None:
            return

        try:
            from mem0 import Memory

            if self._api_key:
                import os
                os.environ.setdefault("OPENAI_API_KEY", self._api_key)

            self._client = Memory.from_config(self._config)
            logger.info("Mem0 provider initialized")
        except ImportError:
            raise ImportError(
                "mem0ai is required for Mem0MemoryProvider. "
                "Install it with: pip install mem0ai"
            )

    def get_store(self) -> MemoryStore:
        return Mem0StoreAdapter(self)

    def get_extractor(self) -> MemoryExtractor:
        """Mem0 自动提取记忆，extractor 为 no-op。"""
        return _Mem0NoOpExtractor()

    def get_embedding_provider(self) -> Any | None:
        """Mem0 内置 embedding，不需要外部 provider。"""
        return None

    async def health_check(self) -> bool:
        try:
            await self.initialize()
            return self._client is not None
        except Exception:
            return False


class Mem0StoreAdapter:
    """将 Mem0 SDK 适配为 MemoryStore 协议。

    Mem0 使用 user_id 隔离记忆，与我们的 user_id 字段直接对应。
    记忆类型通过 metadata.memory_type 存储。
    """

    def __init__(self, provider: Mem0MemoryProvider) -> None:
        self._provider = provider

    async def _ensure_client(self):
        await self._provider.initialize()
        return self._provider._client

    def _mem0_to_record(self, mem: dict) -> MemoryRecord:
        """将 Mem0 记忆转为 MemoryRecord。"""
        metadata = mem.get("metadata", {}) or {}
        memory_type_str = metadata.get("memory_type", "semantic")
        try:
            memory_type = MemoryType(memory_type_str)
        except ValueError:
            memory_type = MemoryType.SEMANTIC

        created_at = mem.get("created_at")
        updated_at = mem.get("updated_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))

        return MemoryRecord(
            id=0,  # Mem0 使用 UUID，这里用 0 占位
            user_id=mem.get("user_id", ""),
            session_id=metadata.get("session_id"),
            memory_type=memory_type,
            content=mem.get("memory", ""),
            summary=metadata.get("summary"),
            source_turn_ids_json=metadata.get("source_turn_ids", []),
            relevance_score=float(mem.get("score", 0)),
            access_count=int(metadata.get("access_count", 0)),
            last_accessed_at_utc=None,
            consolidated_from_json=metadata.get("consolidated_from", []),
            is_active=True,
            expires_at_utc=None,
            created_at_utc=created_at,
            updated_at_utc=updated_at,
        )

    async def save(self, record: MemoryRecord) -> MemoryRecord:
        client = await self._ensure_client()
        messages = [{"role": "user", "content": record.content}]
        metadata = {
            "memory_type": record.memory_type.value,
            "summary": record.summary or "",
            "session_id": record.session_id or "",
            "source_turn_ids": record.source_turn_ids_json,
        }
        result = client.add(
            messages,
            user_id=record.user_id,
            metadata=metadata,
        )
        # Mem0 返回 [{"id": "...", "memory": "...", ...}]
        if result and isinstance(result, list) and len(result) > 0:
            mem = result[0]
            record.id = hash(mem.get("id", "")) % (2**31)
        return record

    async def save_batch(self, records: list[MemoryRecord]) -> list[MemoryRecord]:
        results = []
        for record in records:
            results.append(await self.save(record))
        return results

    async def get(self, memory_id: int) -> MemoryRecord | None:
        client = await self._ensure_client()
        try:
            mem = client.get(str(memory_id))
            if mem:
                return self._mem0_to_record(mem)
        except Exception:
            pass
        return None

    async def search(self, query: MemoryQuery, embedding: list[float]) -> list[MemoryRecord]:
        client = await self._ensure_client()
        results = client.search(
            query.query,
            user_id=query.user_id,
            limit=query.top_k,
        )
        records = []
        for mem in results:
            rec = self._mem0_to_record(mem)
            # 按 memory_type 过滤
            if query.memory_types and rec.memory_type not in query.memory_types:
                continue
            # 按 min_relevance 过滤
            if rec.relevance_score < query.min_relevance:
                continue
            records.append(rec)
        return records

    async def deactivate(self, memory_id: int) -> bool:
        """Mem0 没有 deactivate，使用 delete。"""
        return await self.delete(memory_id)

    async def delete(self, memory_id: int) -> bool:
        client = await self._ensure_client()
        try:
            client.delete(str(memory_id))
            return True
        except Exception:
            return False

    async def list_by_user(
        self,
        user_id: str,
        memory_type: MemoryType | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[MemoryRecord], int]:
        client = await self._ensure_client()
        all_mems = client.get_all(user_id=user_id)
        if not all_mems:
            return [], 0

        # 按类型过滤
        records = []
        for mem in all_mems:
            rec = self._mem0_to_record(mem)
            if memory_type and rec.memory_type != memory_type:
                continue
            records.append(rec)

        total = len(records)
        start = (page - 1) * page_size
        end = start + page_size
        return records[start:end], total

    async def count_by_type(self, user_id: str) -> dict[str, int]:
        client = await self._ensure_client()
        all_mems = client.get_all(user_id=user_id)
        if not all_mems:
            return {}

        counts: dict[str, int] = {}
        for mem in all_mems:
            metadata = mem.get("metadata", {}) or {}
            mtype = metadata.get("memory_type", "semantic")
            counts[mtype] = counts.get(mtype, 0) + 1
        return counts


class _Mem0NoOpExtractor:
    """Mem0 自动提取记忆，此 extractor 为 no-op。"""

    async def extract_episodic(self, messages: list[Any]) -> list[str]:
        return []

    async def extract_semantic(self, messages: list[Any]) -> list[str]:
        return []

    async def extract_procedural(self, messages: list[Any]) -> list[str]:
        return []
