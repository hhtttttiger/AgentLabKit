"""Pydantic request / response schemas for Knowledge Base API.

Field names use camelCase to match the frontend contracts.ts exactly.
Pydantic alias config handles snake_case → camelCase mapping.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import Field

from common.schemas import CamelModel  # noqa: F401 – re-export for backward compat


# ── Knowledge Base ─────────────────────────────────────────────────


class KbCreateRequest(CamelModel):
    name: str
    description: str | None = None
    settings_json: str | None = None


class KbUpdateRequest(CamelModel):
    name: str | None = None
    description: str | None = None
    settings_json: str | None = None


class KbView(CamelModel):
    id: str
    name: str
    description: str | None = None
    source_type: str = "manual"
    document_count: int = 0
    status: str
    settings_json: str | None = None
    metadata_json: str | None = None
    created_at_utc: str
    updated_at_utc: str | None = None


# ── Folder ─────────────────────────────────────────────────────────


class FolderCreateRequest(CamelModel):
    name: str
    parent_folder_id: str | None = None
    sort_order: int = 0


class FolderUpdateRequest(CamelModel):
    name: str | None = None
    sort_order: int | None = None


class FolderMoveRequest(CamelModel):
    target_parent_folder_id: str | None = None


class KbFolderView(CamelModel):
    id: str
    knowledge_base_id: str
    parent_folder_id: str | None = None
    name: str
    sort_order: int
    created_at_utc: str
    updated_at_utc: str | None = None


# ── Document ───────────────────────────────────────────────────────


class QaCreateRequest(CamelModel):
    question: str
    answer: str
    folder_id: str | None = None


class QaUpdateRequest(CamelModel):
    question: str | None = None
    answer: str | None = None


class DocumentMoveRequest(CamelModel):
    target_folder_id: str | None = None


class KbDocumentView(CamelModel):
    id: str
    knowledge_base_id: str
    source_type: str
    stored_file_id: str | None = None
    file_name: str | None = None
    content_type: str | None = None
    file_size: int | None = None
    qa_question: str | None = None
    qa_answer: str | None = None
    ingest_status: str
    ingest_error: str | None = None
    ingested_at_utc: str | None = None
    settings_override_json: str | None = None
    metadata_json: str | None = None
    recall_count: int = 0
    last_recalled_at_utc: str | None = None
    created_at_utc: str
    updated_at_utc: str | None = None
    folder_id: str | None = None
    folder_path: str | None = None


class TopRecalledKbDocumentView(CamelModel):
    document_id: str
    knowledge_base_id: str
    source_type: str
    file_name: str | None = None
    qa_question: str | None = None
    ingest_status: str
    recall_count: int
    last_recalled_at_utc: str | None = None
    created_at_utc: str


# ── Segment ────────────────────────────────────────────────────────


class KbSegmentView(CamelModel):
    id: str
    document_id: str
    segment_index: int
    content: str
    content_type: str | None = None
    metadata_json: str | None = None
    token_count: int | None = None
    created_at_utc: str
    updated_at_utc: str | None = None


# ── Processing ─────────────────────────────────────────────────────


class ProcessingJobView(CamelModel):
    id: str
    document_id: str
    current_stage: str
    stage_progress_json: str | None = None
    error_message: str | None = None
    started_at_utc: str | None = None
    completed_at_utc: str | None = None
    created_at_utc: str
    updated_at_utc: str | None = None


class DocumentIndexView(CamelModel):
    id: str
    document_id: str
    index_type: str
    status: str
    config_json: str | None = None
    stats_json: str | None = None
    built_at_utc: str | None = None
    created_at_utc: str
    updated_at_utc: str | None = None


# ── Search ─────────────────────────────────────────────────────────


class SearchRequest(CamelModel):
    query: str
    top_k: int = 10
    search_mode: Literal["hybrid", "vector", "fulltext"] = "hybrid"


class KbSearchResult(CamelModel):
    segment_id: str
    document_id: str
    content: str
    score: float
    metadata_json: str | None = None
    vector_score: float | None = None
    fulltext_score: float | None = None
    document_name: str | None = None
    document_type: str | None = None


class KbSearchResponse(CamelModel):
    results: list[KbSearchResult]


# ── QA Import ──────────────────────────────────────────────────────


class QaImportError(CamelModel):
    row_number: int
    question: str | None = None
    error_code: str
    message: str


class QaImportResult(CamelModel):
    created_count: int = 0
    updated_count: int = 0
    skipped_count: int = 0
    errors: list[QaImportError] = Field(default_factory=list)
