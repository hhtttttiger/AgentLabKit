"""Explicit registry of business tasks supported by the generic worker."""

from __future__ import annotations

from runtime.worker_runtime import WorkerRegistry


def _create_document_worker_task(settings):
    """Create the document indexing worker task spec."""
    from alkit_infra.queue import QueueSettings
    from modules.knowledge_base.processing import (
        QUEUE_NAME,
        handle_queue_message,
        init_processing_context,
    )
    from runtime.worker_runtime import (
        WorkerCapability,
        WorkerTaskSpec,
    )

    async def handler_factory(context):
        init_processing_context(
            retrieval_service=context.require_retrieval(),
            session_factory=context.session_factory,
            file_storage=context.file_storage,
        )
        return handle_queue_message

    return WorkerTaskSpec(
        name="document_indexing",
        queue_name=QUEUE_NAME,
        handler_factory=handler_factory,
        concurrency=settings.worker.document_indexing_concurrency,
        queue_settings=QueueSettings(),
        required_capabilities=frozenset(
            {WorkerCapability.DATABASE, WorkerCapability.REDIS, WorkerCapability.RETRIEVAL},
        ),
        enabled=lambda value: bool(
            value.retrieval_enabled and value.redis_enabled
        ),
    )


def build_worker_task_registry(settings) -> WorkerRegistry:
    # Deliberately explicit: no directory scanning, entry points or dynamic
    # imports. Adding a task requires a code review at this registry boundary.
    from modules.observability.worker_task import (
        create_worker_task as create_trace_worker_task,
    )

    return WorkerRegistry(
        [
            _create_document_worker_task(settings),
            create_trace_worker_task(settings),
        ],
    )


__all__ = ["build_worker_task_registry"]
