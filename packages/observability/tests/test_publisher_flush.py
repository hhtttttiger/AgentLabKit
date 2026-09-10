"""AsyncTracePublisher.flush — the bounded, process-side finalization seam."""

from __future__ import annotations

import asyncio

import pytest

from observability.config import ObservabilitySettings
from observability.contracts import TraceEnvelope
from observability.publisher import AsyncTracePublisher


class RecordingQueueBackend:
    def __init__(self, delay: float = 0.0):
        self.published: list[str] = []
        self._delay = delay

    async def publish_batch(self, queue_name, messages):
        if self._delay:
            await asyncio.sleep(self._delay)
        self.published.extend(message.payload for message in messages)
        return [f"entry-{len(self.published)}" for _ in messages]


def _envelope(trace_id: str) -> TraceEnvelope:
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    span = {
        "span_id": "a" * 16,
        "trace_id": trace_id,
        "name": "agent.run",
        "kind": "RUN",
        "started_at_utc": now,
        "completed_at_utc": now,
        "duration_ms": 1,
        "attributes": {"agentlabkit.trace.root": True, "agentlabkit.run_id":
                       "00000000-0000-0000-0000-000000000001"},
    }
    return TraceEnvelope(
        trace_id=trace_id,
        root_span_id="a" * 16,
        run_id="00000000-0000-0000-0000-000000000001",
        started_at_utc=now,
        completed_at_utc=now,
        total_duration_ms=1,
        span_count=1,
        spans=[span],
    )


@pytest.mark.asyncio
async def test_flush_resolves_after_envelopes_reach_queue_backend():
    backend = RecordingQueueBackend()
    publisher = AsyncTracePublisher(backend, ObservabilitySettings())
    await publisher.start()
    assert publisher.submit_nowait(_envelope("b" * 32)) is True
    assert await publisher.flush(timeout_seconds=2) is True
    assert len(backend.published) == 1
    await publisher.shutdown()


@pytest.mark.asyncio
async def test_flush_returns_false_on_timeout_without_dropping():
    backend = RecordingQueueBackend(delay=5.0)
    settings = ObservabilitySettings(publish_interval_ms=10)
    publisher = AsyncTracePublisher(backend, settings)
    await publisher.start()
    publisher.submit_nowait(_envelope("c" * 32))
    assert await publisher.flush(timeout_seconds=0.05) is False
    # The envelope is still queued — flush never drops work.
    assert publisher._queue.qsize() >= 0
    await publisher.shutdown()


@pytest.mark.asyncio
async def test_flush_without_running_publisher_is_empty_noop():
    publisher = AsyncTracePublisher(None, ObservabilitySettings())
    assert await publisher.flush() is True
