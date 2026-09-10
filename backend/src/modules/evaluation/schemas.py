from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from common.schemas import CamelModel


class DatasetCreateRequest(CamelModel):
    name: str = Field(max_length=256)
    description: str | None = None
    tags: list[str] = []


class DatasetResponse(CamelModel):
    # Identity is an opaque string on the wire: snowflake ids exceed
    # Number.MAX_SAFE_INTEGER and must never round-trip as JSON numbers.
    id: str
    name: str
    description: str | None = None
    tags: list[str] = []
    case_count: int
    is_active: bool
    created_at_utc: datetime
    updated_at_utc: datetime


class CaseCreateRequest(CamelModel):
    input_text: str
    expected_output: str | None = None
    context: list[str] = []
    tags: list[str] = []


class CaseResponse(CamelModel):
    id: str
    dataset_id: str
    case_index: int
    input_text: str
    expected_output: str | None = None
    context: list[str] = []
    tags: list[str] = []


class RunConfigCreateRequest(CamelModel):
    name: str = Field(max_length=256)
    dataset_id: int
    target_type: str = Field(default="agent", pattern="^(agent|rag_pipeline)$")
    target_key: str = ""
    metric_configs: list[dict[str, Any]] = []
    judge_model_key: str = ""


class RunConfigResponse(CamelModel):
    id: str
    name: str
    dataset_id: str
    target_type: str
    target_key: str
    metric_configs: list[dict[str, Any]]
    judge_model_key: str
    created_at_utc: datetime


class RunResponse(CamelModel):
    id: str
    config_id: str
    status: str
    started_at_utc: datetime | None = None
    completed_at_utc: datetime | None = None
    summary: dict[str, Any]
    created_at_utc: datetime


class MetricEvidenceItem(CamelModel):
    """Bounded retrieval-evidence summary (snake_case storage, camel wire)."""
    availability: str
    attempts: int
    successful_attempts: int
    contexts_used: int
    reason: str | None = None


class MetricResultItem(CamelModel):
    """View over a persisted metric_results_json entry (snake_case storage)."""
    metric_name: str
    score: float | None = None
    reasoning: str | None = None
    passed: bool | None = None
    # Machine-readable unavailable reason (e.g. missing_reference,
    # trace_unavailable); null when the metric produced a score.
    reason: str | None = None
    # Bounded retrieval-evidence summary the metric consumed.
    evidence: MetricEvidenceItem | None = None


class RunResultResponse(CamelModel):
    id: str
    run_id: str
    case_id: str
    actual_output: str
    metric_results: list[MetricResultItem]
    overall_score: float | None
    passed: bool | None = None
    error_message: str | None = None
    duration_ms: int
    # Runtime-owned candidate execution identity (Open Run / Inspect Trace).
    candidate_run_id: str | None = None
    candidate_trace_id: str | None = None


class RunDetailResponse(CamelModel):
    run: RunResponse
    results: list[RunResultResponse]


class EvaluationResultResponse(CamelModel):
    example_id: str
    score: float | None = None
    passed: bool | None = None
    message: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    duration_ms: int = 0


class EvaluationExampleComparisonResponse(CamelModel):
    example_id: str
    classification: str
    left: EvaluationResultResponse | None = None
    right: EvaluationResultResponse | None = None


class CompareEvaluationRunsRequest(CamelModel):
    left_run_id: str
    right_run_id: str


class CompareEvaluationRunsResponse(CamelModel):
    left_run_id: str
    right_run_id: str
    dataset_id: str
    matched_count: int
    left_only_count: int
    right_only_count: int
    examples: list[EvaluationExampleComparisonResponse]


class CompareEvaluationRunsResponseEnvelope(CamelModel):
    success: bool
    msg: str
    data: CompareEvaluationRunsResponse
