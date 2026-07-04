"""Schemas for the model-usage monitoring API (model-monitoring frontend)."""

from __future__ import annotations

from datetime import datetime

from common.schemas import CamelModel


class ModelUsageSummaryResponse(CamelModel):
    model_key: str
    total_requests: int
    success_count: int
    error_count: int
    total_input_tokens: int
    total_output_tokens: int
    total_estimated_cost: float
    avg_duration_ms: float
    total_cache_write_tokens: int = 0
    total_cache_read_tokens: int = 0


class MonitoringOverviewResponse(CamelModel):
    """Aggregated overview: global totals + per-model summaries in one response."""

    total_requests: int
    total_tokens: int
    total_errors: int
    average_latency_ms: float
    model_summaries: list[ModelUsageSummaryResponse]


class UsageRequestViewResponse(CamelModel):
    request_id: str
    model_key: str
    capability: str
    success: bool
    attempt_count: int
    final_instance_key: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    total_input_tokens: int
    total_output_tokens: int
    total_estimated_cost: float
    total_duration_ms: int
    cache_write_tokens: int = 0
    cache_read_tokens: int = 0
    started_at_utc: datetime
    completed_at_utc: datetime


class DistinctErrorCodesResponse(CamelModel):
    error_codes: list[str]


class ErrorRecordViewResponse(CamelModel):
    request_id: str
    model_key: str
    instance_key: str | None = None
    capability: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    duration_ms: int
    started_at_utc: datetime
    completed_at_utc: datetime
