"""Trace ingestion handler used by the generic worker."""

from __future__ import annotations

import time

from alkit_infra.queue import NonRetryableQueueError
from observability import TRACE_SCHEMA_VERSION, TraceEnvelope
from observability.trace_store import PostgresTraceStore
from pydantic import ValidationError


def create_trace_ingestion_handler(
    session_factory,
    *,
    retention_days: int,
    retention_batch_size: int,
):
    store = PostgresTraceStore(session_factory)
    next_retention_at = 0.0

    async def handler(message) -> None:
        nonlocal next_retention_at
        try:
            envelope = TraceEnvelope.model_validate_json(message.payload)
        except ValidationError as exc:
            raise NonRetryableQueueError(f"Invalid trace envelope: {exc}") from exc
        if envelope.schema_version != TRACE_SCHEMA_VERSION:
            raise NonRetryableQueueError(
                f"Unsupported trace schema_version={envelope.schema_version}",
            )

        await store.ingest_trace(envelope)

        now = time.monotonic()
        if now >= next_retention_at:
            await store.delete_expired(
                retention_days=retention_days,
                batch_size=retention_batch_size,
            )
            next_retention_at = now + 24 * 60 * 60

    return handler


def create_worker_task(settings):
    """Export the trace-ingestion task specification."""
    from alkit_infra.queue import QueueSettings
    from observability import ObservabilitySettings, TRACE_QUEUE_NAME
    from runtime.worker_runtime import (
        WorkerCapability,
        WorkerTaskSpec,
    )

    async def handler_factory(context):
        observability_settings = ObservabilitySettings()
        return create_trace_ingestion_handler(
            context.session_factory,
            retention_days=observability_settings.retention_days,
            retention_batch_size=observability_settings.retention_batch_size,
        )

    return WorkerTaskSpec(
        name="trace_ingestion",
        queue_name=TRACE_QUEUE_NAME,
        handler_factory=handler_factory,
        concurrency=settings.worker.trace_ingestion_concurrency,
        queue_settings=QueueSettings(),
        required_capabilities=frozenset(
            {WorkerCapability.DATABASE, WorkerCapability.REDIS},
        ),
        enabled=lambda value: bool(
            value.redis_enabled and ObservabilitySettings().enabled
        ),
    )


__all__ = ["create_trace_ingestion_handler", "create_worker_task"]
