"""TraceIngestionFinalizer — durable trace-ingestion finalization seam.

Critical tests (Evaluation Evidence Finalization closeout):

- T1 read-your-writes: ACK recorded → an immediate wait resolves True.
- T2 ACK race: persistence acknowledged BEFORE the waiter starts still
  resolves immediately (level-observable state, no lost pub/sub wakeup).
- T3 no false success: a Redis that cannot confirm anything never resolves
  the wait — bounded timeout, never a fabricated ACK.
- T4 timeout: no ACK → bounded False.
- TTL: the ACK key is bounded-lifetime state, not a permanent record.
- Cancellation: cancelling the waiter exits immediately, no orphan polling.

Uses the real Redis (same convention as backend db tests); skipped when no
Redis is reachable so the suite stays runnable without infrastructure.
"""

from __future__ import annotations

import asyncio
import os
import time
import uuid

import pytest
import pytest_asyncio
import redis.asyncio as aioredis

from observability.config import ObservabilitySettings
from observability.finalization import (
    ingestion_ack_key,
    TraceIngestionFinalizer,
)

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


def _finalizer(redis_client, **settings) -> TraceIngestionFinalizer:
    return TraceIngestionFinalizer(
        redis_client, settings=ObservabilitySettings(**settings),
    )


def _trace_id() -> str:
    return uuid.uuid4().hex


# ── T1: read-your-writes ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_ack_releases_waiter_immediately(redis_client):
    finalizer = _finalizer(redis_client)
    trace_id = _trace_id()
    # Worker-side: the ACK is recorded only after the durable commit.
    await finalizer.acknowledge_persisted(trace_id)
    started = time.monotonic()
    persisted = await finalizer.wait_until_persisted(
        trace_id, timeout_seconds=2.0,
    )
    assert persisted is True
    # Resolved through the already-observable level state, not by waiting.
    assert time.monotonic() - started < 1.0


# ── T2: ACK race (worker persisted before the waiter started) ────────


@pytest.mark.asyncio
async def test_waiter_starting_after_ack_still_succeeds(redis_client):
    finalizer = _finalizer(redis_client)
    trace_id = _trace_id()
    await finalizer.acknowledge_persisted(trace_id)
    # A brand-new finalizer instance (fresh pub/sub) observes the completion:
    # edge-triggered pub/sub alone would miss this waiter entirely.
    late_waiter = _finalizer(redis_client)
    assert await late_waiter.wait_until_persisted(
        trace_id, timeout_seconds=2.0,
    ) is True


@pytest.mark.asyncio
async def test_commit_between_subscribe_and_check_is_not_lost(redis_client):
    """The classic lost-wakeup race: the ACK lands after the waiter
    subscribed but before its first level check — the wakeup message must
    release it without waiting out the poll interval."""
    finalizer = _finalizer(redis_client)
    trace_id = _trace_id()

    async def commit_soon():
        await asyncio.sleep(0.05)
        await finalizer.acknowledge_persisted(trace_id)

    task = asyncio.create_task(commit_soon())
    started = time.monotonic()
    assert await finalizer.wait_until_persisted(
        trace_id, timeout_seconds=5.0,
    ) is True
    assert time.monotonic() - started < 2.0
    await task


# ── T3: no fabricated success ────────────────────────────────────────


@pytest.mark.asyncio
async def test_unreachable_redis_cannot_confirm_persistence():
    dead = aioredis.from_url("redis://localhost:59999/15", decode_responses=True)
    finalizer = _finalizer(dead)
    started = time.monotonic()
    assert await finalizer.wait_until_persisted(
        "f" * 32, timeout_seconds=0.5,
    ) is False
    assert time.monotonic() - started >= 0.5
    await dead.aclose()


# ── T4: bounded timeout ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_no_ack_times_out_bounded(redis_client):
    finalizer = _finalizer(redis_client)
    trace_id = _trace_id()
    started = time.monotonic()
    assert await finalizer.wait_until_persisted(
        trace_id, timeout_seconds=0.4,
    ) is False
    elapsed = time.monotonic() - started
    assert 0.4 <= elapsed < 2.0


# ── TTL: bounded ACK lifetime ────────────────────────────────────────


@pytest.mark.asyncio
async def test_ack_key_has_bounded_lifetime(redis_client):
    finalizer = _finalizer(redis_client, finalization_ack_ttl_seconds=1)
    trace_id = _trace_id()
    await finalizer.acknowledge_persisted(trace_id)
    ttl = await redis_client.ttl(ingestion_ack_key(trace_id))
    assert 0 < ttl <= 1


# ── Cancellation ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_waiter_cancellation_exits_immediately(redis_client):
    finalizer = _finalizer(redis_client)
    trace_id = _trace_id()
    task = asyncio.create_task(
        finalizer.wait_until_persisted(trace_id, timeout_seconds=30.0),
    )
    await asyncio.sleep(0.1)
    started = time.monotonic()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert time.monotonic() - started < 1.0
