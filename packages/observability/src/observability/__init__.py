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
from .trace_store import PostgresTraceStore, TraceStore


def __getattr__(name: str):
    """Lazy import for OTel-heavy modules."""
    if name == "TraceBufferSpanProcessor":
        from .span_processor import TraceBufferSpanProcessor
        return TraceBufferSpanProcessor
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


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
