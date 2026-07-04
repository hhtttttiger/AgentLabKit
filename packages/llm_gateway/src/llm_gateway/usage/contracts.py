from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class UsageRequestRecord:
    request_id: str
    model_key: str
    capability: str  # e.g. "text", "speech_batch"
    success: bool
    attempt_count: int
    final_instance_key: str | None
    error_code: str | None
    error_message: str | None
    total_input_tokens: int
    total_output_tokens: int
    total_estimated_cost: float
    cache_write_tokens: int
    cache_read_tokens: int
    total_duration_ms: int
    started_at_utc: datetime
    completed_at_utc: datetime


@dataclass(frozen=True, slots=True)
class UsageAttemptRecord:
    request_id: str
    model_key: str
    instance_key: str
    attempt_no: int
    success: bool
    error_code: str | None
    error_message: str | None
    input_tokens: int | None
    output_tokens: int | None
    estimated_cost: float | None
    cache_write_tokens: int | None
    cache_read_tokens: int | None
    duration_ms: int
    started_at_utc: datetime
    completed_at_utc: datetime
