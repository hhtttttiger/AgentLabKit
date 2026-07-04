from __future__ import annotations

from datetime import datetime

from pydantic import Field, field_validator

from common.schemas import CamelModel
from memory.contracts import MemoryType


class MemoryItem(CamelModel):
    id: int
    user_id: str
    session_id: str | None = None
    memory_type: str
    content: str
    summary: str | None = None
    relevance_score: float
    access_count: int
    is_active: bool
    created_at_utc: datetime
    updated_at_utc: datetime


class MemoryStatsResponse(CamelModel):
    user_id: str
    counts_by_type: dict[str, int]
    total_active: int


class MemorySearchRequest(CamelModel):
    query: str
    memory_types: list[str] | None = None
    top_k: int = Field(default=5, ge=1, le=20)


class ConsolidateRequest(CamelModel):
    memory_type: str = Field(default="episodic")
    batch_size: int = Field(default=10, ge=3, le=50)

    @field_validator("memory_type")
    @classmethod
    def validate_memory_type(cls, v: str) -> str:
        try:
            MemoryType(v)
        except ValueError:
            allowed = ", ".join(e.value for e in MemoryType)
            raise ValueError(f"Invalid memory_type '{v}'. Must be one of: {allowed}")
        return v
