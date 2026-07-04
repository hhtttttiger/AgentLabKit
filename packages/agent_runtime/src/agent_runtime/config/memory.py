from __future__ import annotations

from pydantic import BaseModel


class MemorySettings(BaseModel):
    enabled: bool = False
    persist_sessions: bool = False
    max_total_tokens: int = 8000
    reserve_for_response: int = 1500
    reserve_for_system: int = 1500
    summarize_threshold_ratio: float = 0.8
    min_recent_messages: int = 4
    enable_summarization: bool = True
    summarization_model: str | None = None
    tokenizer_model: str = "gpt-5.4-mini"
