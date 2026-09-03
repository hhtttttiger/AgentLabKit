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
    id: int
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
    id: int
    dataset_id: int
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
    id: int
    name: str
    dataset_id: int
    target_type: str
    target_key: str
    metric_configs: list[dict[str, Any]]
    judge_model_key: str
    created_at_utc: datetime


class RunResponse(CamelModel):
    id: int
    config_id: int
    status: str
    started_at_utc: datetime | None = None
    completed_at_utc: datetime | None = None
    summary: dict[str, Any] = {}
    created_at_utc: datetime


class RunResultResponse(CamelModel):
    id: int
    run_id: int
    case_id: int
    actual_output: str
    metric_results: list[dict[str, Any]]
    overall_score: float
    passed: bool | None = None
    error_message: str | None = None
    duration_ms: int


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
