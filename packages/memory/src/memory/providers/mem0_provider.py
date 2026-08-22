"""Mem0MemoryProvider — 适配 Mem0 开源记忆库。

Mem0 内置记忆提取、去重、合并，因此 extractor 为 no-op。
记忆类型通过 metadata 存储，检索时按类型过滤。

依赖：pip install mem0ai
"""

from __future__ import annotations

import asyncio
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
        # 缓存 store / extractor 实例，避免重复创建
        # Mem0StoreAdapter 内部维护 ID 映射，必须复用同一实例
        self._store = Mem0StoreAdapter(self)
        self._extractor = _Mem0NoOpExtractor()

    async def initialize(self) -> None:
        """延迟初始化 Mem0 客户端。"""
        if self._client is not None:
            return

        try:
            from mem0 import Memory
        except ImportError:
            raise ImportError(
                "mem0ai is required for Mem0MemoryProvider. "
                "Install it with: pip install mem0ai"
            )

        # 通过 config dict 传递 api_key，避免污染全局环境变量
        init_config = dict(self._config)
        if self._api_key:
            init_config.setdefault("api_key", self._api_key)

        self._client = await asyncio.to_thread(Memory.from_config, init_config)
        logger.info("Mem0 provider initialized")

    def get_store(self) -> MemoryStore:
        """返回缓存的 store 适配器（内部维护 ID 映射，必须复用）。"""
        return self._store

    def get_extractor(self) -> MemoryExtractor:
        """Mem0 自动提取记忆，extractor 为 no-op。"""
        return self._extractor

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

    Mem0 使用 UUID 标识记忆，我们的 MemoryStore 使用 int ID。
    本适配器维护 int ↔ UUID 双向映射，保证 save→get→delete 链路正确。

    Mem0 使用 user_id 隔离记忆，与我们的 user_id 字段直接对应。
    记忆类型通过 metadata.memory_type 存储。
    """

    def __init__(self, provider: Mem0MemoryProvider) -> None:
        self._provider = provider
        # int_id ↔ mem0_uuid 双向映射
        self._id_map: dict[int, str] = {}       # int_id -> mem0_uuid
        self._reverse_map: dict[str, int] = {}   # mem0_uuid -> int_id
        self._counter = 0

    def _to_int_id(self, mem0_uuid: str) -> int:
        """将 Mem0 UUID 映射为 int ID（幂等：相同 UUID 返回相同 int）。"""
        if mem0_uuid in self._reverse_map:
            return self._reverse_map[mem0_uuid]
        self._counter += 1
        int_id = self._counter
        self._id_map[int_id] = mem0_uuid
        self._reverse_map[mem0_uuid] = int_id
        return int_id

    def _to_mem0_id(self, int_id: int) -> str | None:
        """将 int ID 映射回 Mem0 UUID。"""
        return self._id_map.get(int_id)

    async def _ensure_client(self):
        await self._provider.initialize()
        return self._provider._client

    def _mem0_to_record(self, mem: dict, int_id: int = 0) -> MemoryRecord:
        """将 Mem0 记忆转为 MemoryRecord。

        Args:
            mem: Mem0 返回的记忆字典。
            int_id: 已映射的 int ID。为 0 时从 mem["id"] 映射。
        """
        if int_id == 0:
            mem0_uuid = mem.get("id", "")
            int_id = self._to_int_id(mem0_uuid) if mem0_uuid else 0

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
            id=int_id,
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
        result = await asyncio.to_thread(
            client.add,
            messages,
            user_id=record.user_id,
            metadata=metadata,
        )
        # Mem0 返回 [{"id": "...", "memory": "...", ...}]
        if result and isinstance(result, list) and len(result) > 0:
            mem = result[0]
            mem0_id = mem.get("id", "")
            record.id = self._to_int_id(mem0_id)
        return record

    async def save_batch(self, records: list[MemoryRecord]) -> list[MemoryRecord]:
        results = []
        for record in records:
            results.append(await self.save(record))
        return results

    async def get(self, memory_id: int) -> MemoryRecord | None:
        mem0_id = self._to_mem0_id(memory_id)
        if not mem0_id:
            return None
        client = await self._ensure_client()
        try:
            mem = await asyncio.to_thread(client.get, mem0_id)
            if mem:
                return self._mem0_to_record(mem, int_id=memory_id)
        except Exception:
            pass
        return None

    async def search(
        self,
        query: MemoryQuery,
        embedding: list[float],
    ) -> list[MemoryRecord]:
        """检索记忆。

        Note:
            ``embedding`` 参数为 MemoryStore Protocol 兼容保留，
            Mem0 内部自行处理 embedding，此参数被忽略。
        """
        client = await self._ensure_client()
        results = await asyncio.to_thread(
            client.search,
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
        mem0_id = self._to_mem0_id(memory_id)
        if not mem0_id:
            return False
        client = await self._ensure_client()
        try:
            await asyncio.to_thread(client.delete, mem0_id)
            # 清理映射
            self._id_map.pop(memory_id, None)
            self._reverse_map.pop(mem0_id, None)
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
        all_mems = await asyncio.to_thread(client.get_all, user_id=user_id)
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
        all_mems = await asyncio.to_thread(client.get_all, user_id=user_id)
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
