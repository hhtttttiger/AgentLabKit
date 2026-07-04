from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class MemoryType(str, Enum):
    EPISODIC = "episodic"       # 对话摘要
    SEMANTIC = "semantic"       # 提取的事实性知识
    PROCEDURAL = "procedural"   # 用户偏好 / 行为模式


@dataclass(slots=True)
class MemoryRecord:
    """一条长期记忆。"""
    id: int = 0
    user_id: str = ""
    session_id: str | None = None
    memory_type: MemoryType = MemoryType.EPISODIC
    content: str = ""
    summary: str | None = None
    source_turn_ids_json: list[str] = field(default_factory=list)
    relevance_score: float = 0.0
    access_count: int = 0
    last_accessed_at_utc: datetime | None = None
    consolidated_from_json: list[int] = field(default_factory=list)
    is_active: bool = True
    expires_at_utc: datetime | None = None
    created_at_utc: datetime | None = None
    updated_at_utc: datetime | None = None


@dataclass(slots=True)
class MemoryQuery:
    """记忆检索请求。"""
    user_id: str = ""
    query: str = ""
    memory_types: list[MemoryType] | None = None
    top_k: int = 5
    min_relevance: float = 0.5
