"""OpenTelemetry-based tracing and PostgreSQL query support."""

from .config import ObservabilitySettings
from .contracts import (
    SpanEnvelope,
    SpanRecord,
    TRACE_QUEUE_NAME,
    TRACE_SCHEMA_VERSION,
    TraceEnvelope,
    TracePage,
    TraceRecord,
    TraceStats,
)
from .module import ObservabilityModule, create_observability_module
from .publisher import AsyncTracePublisher
from .span_processor import TraceBufferSpanProcessor
from .trace_store import PostgresTraceStore, TraceStore

__all__ = [
    "AsyncTracePublisher",
    "ObservabilityModule",
    "ObservabilitySettings",
    "PostgresTraceStore",
    "SpanEnvelope",
    "SpanRecord",
    "TRACE_QUEUE_NAME",
    "TRACE_SCHEMA_VERSION",
    "TraceBufferSpanProcessor",
    "TraceEnvelope",
    "TracePage",
    "TraceRecord",
    "TraceStats",
    "TraceStore",
    "create_observability_module",
]
