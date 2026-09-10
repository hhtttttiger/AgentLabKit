"""Trace ingestion worker finalization: ACK only after the durable commit.

- T1 read-your-writes (production shape): the worker handler ingests the
  envelope through the real PostgresTraceStore, records the finalization
  ACK after the commit, and an immediate TraceReader read sees the trace —
  no sleep, no polling, no "eventually" helper.
- T3 DB failure: a failed ingest must never record a success ACK, so no
  consumer can be released to read a trace that does not exist.

Requires a running PostgreSQL (see conftest) and Redis.
"""

from __future__ import annotations

import os
import uuid

import pytest
import pytest_asyncio
import redis.asyncio as aioredis

from observability.contracts import TraceEnvelope
from observability.finalization import ingestion_ack_key
from observability.trace_store import PostgresTraceStore

_REDIS_URL = os.environ.get("TEST_REDIS_URL", "redis://localhost:6379/15")


@pytest_asyncio.fixture
async def redis_client():
    client = aioredis.from_url(_REDIS_URL, decode_responses=True)
    try:
        await client.ping()
    except Exception as exc:  # pragma: no cover — infra guard
        pytest.skip(f"test redis unavailable at {_REDIS_URL}: {exc}")
    yield client
    await client.aclose()


def _envelope(trace_id: str) -> TraceEnvelope:
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    span = {
        "span_id": "a" * 16,
        "trace_id": trace_id,
        "name": "agent.run",
        "kind": "agent",
        "started_at_utc": now,
        "completed_at_utc": now,
        "duration_ms": 1,
        "attributes": {
            "agentlabkit.trace.root": True,
            "agentlabkit.run_id": "00000000-0000-0000-0000-000000000001",
        },
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


class _Message:
    def __init__(self, payload: str) -> None:
        self.payload = payload


def _build_handler(db_session_factory, redis_client):
    from modules.observability.worker_task import create_trace_ingestion_handler
    from observability.finalization import TraceIngestionFinalizer
    from observability.config import ObservabilitySettings

    settings = ObservabilitySettings()
    return create_trace_ingestion_handler(
        db_session_factory,
        retention_days=settings.retention_days,
        retention_batch_size=settings.retention_batch_size,
        finalizer=TraceIngestionFinalizer(redis_client, settings=settings),
    )


@pytest.mark.db
async def test_worker_commit_acks_and_trace_is_immediately_readable(
    db_session_factory, redis_client,
):
    handler = _build_handler(db_session_factory, redis_client)
    trace_id = uuid.uuid4().hex
    store = PostgresTraceStore(db_session_factory)

    await handler(_Message(_envelope(trace_id).model_dump_json()))

    # No sleep/poll: the ACK is the contract that read-your-writes holds.
    from observability.finalization import TraceIngestionFinalizer

    finalizer = TraceIngestionFinalizer(redis_client)
    assert await finalizer.wait_until_persisted(trace_id, timeout_seconds=2.0)
    spans = await store.get_trace_spans(trace_id)
    assert [span.name for span in spans] == ["agent.run"]


@pytest.mark.db
async def test_failed_ingest_records_no_success_ack(
    db_session_factory, redis_client, monkeypatch,
):
    from modules.observability import worker_task
    from observability.finalization import TraceIngestionFinalizer
    from observability.config import ObservabilitySettings

    class _ExplodingStore:
        def __init__(self, session_factory) -> None:
            pass

        async def ingest_trace(self, envelope) -> None:
            raise RuntimeError("simulated commit failure")

    monkeypatch.setattr(worker_task, "PostgresTraceStore", _ExplodingStore)
    settings = ObservabilitySettings()
    handler = worker_task.create_trace_ingestion_handler(
        db_session_factory,
        retention_days=settings.retention_days,
        retention_batch_size=settings.retention_batch_size,
        finalizer=TraceIngestionFinalizer(redis_client, settings=settings),
    )
    trace_id = uuid.uuid4().hex

    with pytest.raises(RuntimeError, match="simulated commit failure"):
        await handler(_Message(_envelope(trace_id).model_dump_json()))

    assert await redis_client.get(ingestion_ack_key(trace_id)) is None
    finalizer = TraceIngestionFinalizer(redis_client)
    assert not await finalizer.wait_until_persisted(trace_id, timeout_seconds=0.3)
