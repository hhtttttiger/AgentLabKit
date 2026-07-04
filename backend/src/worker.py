"""文档索引队列消费者 —— 独立 worker 进程。

与 web 进程分离的生产者/消费者模型：
- **web 进程**只 ``enqueue``（生产者），HTTP 请求处理与索引处理互不阻塞；
- **本 worker**消费 ``document_processing`` 队列（消费者），执行分块 +
  embedding + 向量存储等 CPU/IO/内存密集操作。

设计要点：
- 共享内核：复用 ``runtime.bootstrap`` 构造 gateway/retrieval，与 web 同源；
- 最小职责：不加载 HTTP / 路由 / agent_runtime 等无关模块；
- 优雅退出：SIGINT/SIGTERM → drain 在途消息 → 释放连接；
- 可扩展：多实例时各自用不同 ``consumer_name``，Redis Streams 同组内不同
  consumer 即并行分摊负载（水平扩展靠多实例，而非调大单进程并发）。

本地启动：
    cd backend && PYTHONPATH=src:../packages/llm_gateway/src:../packages/agent_runtime/src python -m worker
（其余包经 editable install 装入 venv）。
"""

from __future__ import annotations

import asyncio
import os
import signal
import socket

from loguru import logger

from config import Settings
from alkit_db.engine import get_session_factory
from alkit_infra.queue import QueueConsumer, QueueSettings, RedisStreamsQueue
from modules.knowledge_base.processing import (
    QUEUE_NAME,
    handle_queue_message,
    init_processing_context,
)
from runtime.bootstrap import (
    build_gateway_service,
    build_retrieval_service,
    cleanup_infrastructure,
    init_infrastructure,
)

# 单进程内 asyncio 并发数。水平扩展靠多实例，不靠调大此值（吃单核上限）。
_CONCURRENCY = int(os.environ.get("APP_WORKER_CONCURRENCY", "3"))
# 同组内必须唯一，否则多实例会合并成同一个 consumer 的 PEL（无法并行）。
_DEFAULT_CONSUMER_NAME = f"doc-worker-{socket.gethostname()}"


async def _run(settings: Settings) -> None:
    consumer_name = os.environ.get("APP_WORKER_CONSUMER_NAME", _DEFAULT_CONSUMER_NAME)
    logger.info(
        "Starting document-indexing worker "
        "(queue={}, consumer={}, concurrency={})",
        QUEUE_NAME,
        consumer_name,
        _CONCURRENCY,
    )

    # ── 共享内核：装配基础设施（与 web 同源，非复制粘贴）──
    # socket_timeout 必须 > consumer 的 poll_timeout_ms（默认 5s）：XREADGROUP 会
    # 阻塞等待消息，若 socket 超时 ≤ 阻塞时间，阻塞读会被掐断成 TimeoutError
    # （redis-py 的 socket_timeout 覆盖整条命令，含阻塞读阶段）。
    init_infrastructure(settings, socket_timeout=30.0)
    gateway_service = build_gateway_service(settings)
    retrieval_service = build_retrieval_service(settings, gateway_service)

    # 消费 handler 依赖的运行时上下文（模块级全局，见 processing.init_processing_context）
    init_processing_context(
        retrieval_service=retrieval_service,
        session_factory=get_session_factory(),
    )

    queue = RedisStreamsQueue(settings=QueueSettings())
    consumer = QueueConsumer(
        backend=queue,
        queue_name=QUEUE_NAME,
        consumer_name=consumer_name,
        handler=handle_queue_message,
        concurrency=_CONCURRENCY,
    )
    await consumer.start()

    # ── 优雅退出：SIGINT/SIGTERM → set event → drain 在途消息 → 释放连接 ──
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop_event.set)

    logger.info("Worker ready, waiting for messages (Ctrl-C to stop)")
    await stop_event.wait()

    logger.info("Shutdown signal received, draining in-flight messages...")
    await consumer.stop(timeout=30.0)
    await queue.close()
    await cleanup_infrastructure()
    logger.info("Worker stopped cleanly")


def main() -> None:
    settings = Settings()

    # 前置校验：worker 在 retrieval / redis 未启用时没有意义，直接退出。
    if not settings.retrieval_enabled:
        logger.error(
            "APP_RETRIEVAL_ENABLED is false — worker has nothing to index, exiting"
        )
        raise SystemExit(1)
    if not settings.redis_enabled:
        logger.error(
            "APP_REDIS_ENABLED is false — worker needs the queue, exiting"
        )
        raise SystemExit(1)

    try:
        asyncio.run(_run(settings))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
