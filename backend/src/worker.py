"""Generic queue worker supervisor.

The process owns infrastructure lifecycle only. Business tasks are explicitly
registered in :mod:`runtime.worker_modules` and receive typed dependencies.
"""

from __future__ import annotations

import asyncio
import signal

from alkit_db.engine import get_session_factory
from alkit_infra.queue import RedisStreamsQueue
from loguru import logger

from config import Settings
from runtime.bootstrap import (
    build_file_storage,
    build_gateway_service,
    build_retrieval_service,
    cleanup_infrastructure,
    init_infrastructure,
)
from runtime.worker_modules import build_worker_task_registry
from runtime.worker_runtime import WorkerCapability, WorkerContext, WorkerSupervisor


async def _run(settings: Settings) -> None:
    if not settings.redis_enabled:
        raise RuntimeError("Generic worker requires APP_REDIS_ENABLED=true")

    registry = build_worker_task_registry(settings)
    specs = registry.select(settings.worker.tasks, settings)
    if not specs:
        raise RuntimeError("Worker has no enabled tasks")

    capabilities = set().union(*(spec.required_capabilities for spec in specs))
    if WorkerCapability.RETRIEVAL in capabilities:
        capabilities.add(WorkerCapability.GATEWAY)

    logger.info(
        "Starting worker id={} tasks={} capabilities={}",
        settings.worker.resolved_worker_id,
        [spec.name for spec in specs],
        sorted(item.value for item in capabilities),
    )

    init_infrastructure(settings, socket_timeout=30.0)
    queue: RedisStreamsQueue | None = None
    supervisor: WorkerSupervisor | None = None
    try:
        queue = RedisStreamsQueue()
        gateway = (
            build_gateway_service(settings)
            if WorkerCapability.GATEWAY in capabilities
            else None
        )
        retrieval = (
            build_retrieval_service(settings, gateway)
            if WorkerCapability.RETRIEVAL in capabilities
            else None
        )
        file_storage = build_file_storage(settings)
        context = WorkerContext(
            settings=settings,
            session_factory=get_session_factory(),
            queue_backend=queue,
            gateway_service=gateway,
            retrieval_service=retrieval,
            file_storage=file_storage,
        )
        supervisor = WorkerSupervisor(
            context,
            specs,
            worker_id=settings.worker.resolved_worker_id,
        )
        stop_event = asyncio.Event()
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, stop_event.set)
            except NotImplementedError:
                signal.signal(sig, lambda *_: loop.call_soon_threadsafe(stop_event.set))

        await supervisor.start()
        signal_wait = asyncio.create_task(stop_event.wait(), name="worker:signal")
        failure_wait = asyncio.create_task(
            supervisor.wait_for_failure(),
            name="worker:failure",
        )
        done, pending = await asyncio.wait(
            {signal_wait, failure_wait},
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)
        if failure_wait in done:
            await failure_wait
    finally:
        logger.info("Worker shutdown started")
        try:
            if supervisor is not None:
                await supervisor.stop(
                    timeout=settings.worker.shutdown_timeout_seconds,
                )
        finally:
            if queue is not None:
                await queue.close()
            await cleanup_infrastructure()
        logger.info("Worker shutdown completed")


def main() -> None:
    try:
        asyncio.run(_run(Settings()))
    except KeyboardInterrupt:
        pass
    except Exception:
        logger.exception("Worker stopped because of a fatal error")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
