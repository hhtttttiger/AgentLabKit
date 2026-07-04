"""MemoryConsolidator — 合并/摘要旧记忆。"""

from __future__ import annotations

from typing import Any

from .contracts import MemoryRecord, MemoryType


class MemoryConsolidator:
    """将同用户的旧 episodic 记忆合并为更高层摘要。

    流程：
    1. 查询用户的老旧 episodic 记忆（按 access_count 升序）
    2. 用 LLM 合并为一条摘要
    3. 旧记忆 deactivated，新记忆写入
    """

    def __init__(self, store: Any, extractor: Any) -> None:
        self._store = store
        self._extractor = extractor

    async def consolidate(
        self,
        user_id: str,
        memory_type: MemoryType = MemoryType.EPISODIC,
        batch_size: int = 10,
    ) -> int:
        """执行一次整合。返回合并的记忆数。"""
        # 1. 获取需要整合的旧记忆
        records, total = await self._store.list_by_user(
            user_id, memory_type=memory_type, page=1, page_size=batch_size,
        )

        if len(records) < 3:
            return 0  # 太少，不值得整合

        # 2. 构造合并内容
        contents = [r.content for r in records]
        merged_text = "\n".join(f"- {c}" for c in contents)

        # 3. 用 extractor 做摘要
        try:
            from llm_gateway.models import TextGenerateRequest

            prompt = (
                "请将以下多条对话摘要合并为一条简洁的高层摘要（2-3句话），"
                "保留关键事实和结论：\n\n"
                f"{merged_text}"
            )

            # 使用 extractor 的 gateway 来生成摘要
            if hasattr(self._extractor, '_gateway'):
                request = TextGenerateRequest(
                    messages=[{"role": "user", "content": prompt}],
                    model=getattr(self._extractor, '_model', "") or None,
                    max_tokens=256,
                    temperature=0.1,
                )
                response = await self._extractor._gateway.generate_text(request)
                summary = response.choices[0].message.content if response.choices else ""
            else:
                summary = merged_text[:500]  # fallback: truncate
        except Exception:
            summary = merged_text[:500]

        if not summary or len(summary) < 10:
            return 0

        # 4. 创建新的整合记忆
        new_record = MemoryRecord(
            user_id=user_id,
            memory_type=memory_type,
            content=summary,
            summary="Consolidated from older memories",
            consolidated_from_json=[r.id for r in records],
            relevance_score=max(r.relevance_score for r in records),
        )
        saved = await self._store.save(new_record)

        # 5. 保存 embedding
        if hasattr(self._store, 'save_embedding'):
            # 需要一个 embedding provider — 这里简化处理
            pass

        # 6. Deactivate 旧记忆
        for r in records:
            await self._store.deactivate(r.id)

        return len(records)
