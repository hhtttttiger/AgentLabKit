from __future__ import annotations

import asyncio
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Awaitable, Callable

from alkit_infra.queue import Message, QueueBackend, QueueConsumer, QueueSettings
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

if TYPE_CHECKING:
    from config import Settings
    from llm_gateway import GatewayService
    from modules.knowledge_base.retrieval_service import KnowledgeRetrievalService


class WorkerCapability(StrEnum):
    DATABASE = "database"
    REDIS = "redis"
    GATEWAY = "gateway"
    RETRIEVAL = "retrieval"


@dataclass(slots=True)
class WorkerContext:
    settings: Settings
    session_factory: async_sessionmaker[AsyncSession]
    queue_backend: QueueBackend
    gateway_service: GatewayService | None = None
    retrieval_service: KnowledgeRetrievalService | None = None

    def require_gateway(self) -> GatewayService:
        if self.gateway_service is None:
            raise RuntimeError("Worker task requires gateway capability")
        return self.gateway_service

    def require_retrieval(self) -> KnowledgeRetrievalService:
        if self.retrieval_service is None:
            raise RuntimeError("Worker task requires retrieval capability")
        return self.retrieval_service


WorkerHandlerFactory = Callable[
    [WorkerContext],
    Awaitable[Callable[[Message], Awaitable[None]]],
]


@dataclass(frozen=True, slots=True)
class WorkerTaskSpec:
    name: str
    queue_name: str
    handler_factory: WorkerHandlerFactory
    concurrency: int
    queue_settings: QueueSettings
    required_capabilities: frozenset[WorkerCapability]
    enabled: Callable[[Settings], bool]

    def __post_init__(self) -> None:
        if not self.name.strip() or not self.queue_name.strip():
            raise ValueError("Worker task name and queue_name must be non-empty")
        if self.concurrency < 1:
            raise ValueError("Worker task concurrency must be at least 1")


class WorkerRegistry:
    def __init__(self, specs: list[WorkerTaskSpec]) -> None:
        names = [spec.name for spec in specs]
        queues = [spec.queue_name for spec in specs]
        if len(names) != len(set(names)):
            raise ValueError("Worker task names must be unique")
        if len(queues) != len(set(queues)):
            raise ValueError("Worker queue names must be unique")
        self._specs = {spec.name: spec for spec in specs}

    def select(self, selection: str, settings: Settings) -> list[WorkerTaskSpec]:
        if selection.strip() in {"", "*"}:
            selected = [spec for spec in self._specs.values() if spec.enabled(settings)]
            for spec in self._specs.values():
                if spec not in selected:
                    logger.info("Worker task {} skipped (disabled)", spec.name)
            return selected

        requested = {name.strip() for name in selection.split(",") if name.strip()}
        unknown = requested.difference(self._specs)
        if unknown:
            raise ValueError(f"Unknown worker tasks: {', '.join(sorted(unknown))}")
        selected = [self._specs[name] for name in sorted(requested)]
        disabled = [spec.name for spec in selected if not spec.enabled(settings)]
        if disabled:
            available = {
                WorkerCapability.DATABASE,
                *(
                    [WorkerCapability.REDIS]
                    if getattr(settings, "redis_enabled", False)
                    else []
                ),
                *(
                    [WorkerCapability.GATEWAY, WorkerCapability.RETRIEVAL]
                    if getattr(settings, "retrieval_enabled", False)
                    else []
                ),
            }
            details = []
            for spec in selected:
                if spec.name not in disabled:
                    continue
                missing = sorted(
                    item.value
                    for item in spec.required_capabilities.difference(available)
                )
                details.append(
                    f"{spec.name} (missing: {', '.join(missing) or 'task configuration'})",
                )
            raise RuntimeError(
                "Explicitly selected worker tasks are unavailable: "
                + "; ".join(details),
            )
        return selected


class WorkerSupervisor:
    def __init__(self, context: WorkerContext, specs: list[WorkerTaskSpec], worker_id: str) -> None:
        self._context = context
        self._specs = specs
        self._worker_id = worker_id
        self._consumers: list[tuple[WorkerTaskSpec, QueueConsumer]] = []

    async def start(self) -> None:
        initialized: list[tuple[WorkerTaskSpec, Any]] = []
        for spec in self._specs:
            handler = await spec.handler_factory(self._context)
            initialized.append((spec, handler))

        for spec, handler in initialized:
            consumer = QueueConsumer(
                backend=self._context.queue_backend,
                queue_name=spec.queue_name,
                consumer_name=f"{self._worker_id}:{spec.name}",
                handler=handler,
                concurrency=spec.concurrency,
                settings=spec.queue_settings,
            )
            await consumer.start()
            self._consumers.append((spec, consumer))
            backlog = await self._context.queue_backend.queue_stats(spec.queue_name)
            logger.info(
                "Worker task started name={} queue={} concurrency={} capabilities={} backlog={}",
                spec.name,
                spec.queue_name,
                spec.concurrency,
                sorted(item.value for item in spec.required_capabilities),
                backlog,
            )

    async def wait_for_failure(self) -> None:
        if not self._consumers:
            raise RuntimeError("Worker has no enabled tasks")
        waits = [asyncio.create_task(consumer.wait(), name=f"watch:{spec.name}") for spec, consumer in self._consumers]
        try:
            done, pending = await asyncio.wait(
                waits,
                return_when=asyncio.FIRST_COMPLETED,
            )
        finally:
            pending = {task for task in waits if not task.done()}
            for task in pending:
                task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)
        for task in done:
            exception = task.exception()
            if exception is not None:
                raise exception
        raise RuntimeError("Worker consumer exited unexpectedly")

    async def stop(self, timeout: float = 30.0) -> None:
        await asyncio.gather(
            *(consumer.stop(timeout=timeout) for _, consumer in reversed(self._consumers)),
            return_exceptions=False,
        )
        for spec, consumer in self._consumers:
            logger.info(
                "Worker task stopped name={} processed={} failed={} inflight={}",
                spec.name,
                consumer.processed_count,
                consumer.failed_count,
                consumer.inflight_count,
            )


__all__ = [
    "WorkerCapability",
    "WorkerContext",
    "WorkerRegistry",
    "WorkerSupervisor",
    "WorkerTaskSpec",
]
