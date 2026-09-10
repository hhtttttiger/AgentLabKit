"""Durable trace-ingestion finalization seam.

``publish`` / ``flush`` proves the envelope reached Redis; only the worker's
Postgres commit makes the authoritative trace projection readable.  This seam
carries that fact to synchronous consumers:

    worker commit  →  acknowledge(trace_id)   [after COMMIT success]
    consumer       →  wait_until_persisted(trace_id, timeout)

The ACK is level-observable state (a TTL-bounded Redis key) with a pub/sub
wakeup on top.  A pure pub/sub signal is edge-triggered: a waiter starting
after the worker committed would miss it and time out against a trace that
is already readable.  Waiting therefore subscribes *first*, checks the key,
and re-checks it on every wakeup — the key is the truth, the message is
only a latency optimization.

The ACK belongs to Observability infrastructure.  Consumers (Evaluation,
replay, future synchronous readers) await this narrow contract; they never
poll storage, inspect Redis, or know worker internals.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from .config import ObservabilitySettings

logger = logging.getLogger(__name__)

TRACE_INGESTED_KEY_PREFIX = "trace_ingested"
#: Pub/sub wakeup channel.  Carries trace_ids; the key carries the truth.
TRACE_INGESTED_CHANNEL = "observability_trace_ingested"
_WAKEUP_POLL_SECONDS = 0.5


def ingestion_ack_key(trace_id: str) -> str:
    return f"{TRACE_INGESTED_KEY_PREFIX}:{trace_id}"


class TraceIngestionFinalizer:
    """Trace-persistence ACK keyed by trace_id (multi-process safe).

    ``acknowledge_persisted`` is called by the ingestion worker strictly
    after the Postgres transaction commits; a failed commit never produces
    a success ACK.  ``wait_until_persisted`` resolves once that ACK is
    observable — including for waiters that start after it was recorded —
    or returns False when the bounded timeout passes.
    """

    def __init__(
        self,
        redis: Any | None = None,
        settings: ObservabilitySettings | None = None,
    ) -> None:
        self._redis = redis
        self._settings = settings or ObservabilitySettings()

    def _client(self) -> Any:
        if self._redis is None:
            from alkit_infra.redis.client import get_redis

            self._redis = get_redis()
        return self._redis

    async def acknowledge_persisted(self, trace_id: str) -> None:
        """Record the durable-commit ACK (level state + wakeup message).

        Must only be called after the authoritative projection is committed;
        callers run it after the store call returns, never on failure paths.
        """
        redis = self._client()
        await redis.set(
            ingestion_ack_key(trace_id),
            "1",
            ex=self._settings.finalization_ack_ttl_seconds,
        )
        await redis.publish(TRACE_INGESTED_CHANNEL, trace_id)

    async def wait_until_persisted(
        self,
        trace_id: str,
        *,
        timeout_seconds: float,
    ) -> bool:
        """Bounded wait for the durable-commit ACK of ``trace_id``.

        Returns True once the trace projection is readable (read-your-writes),
        False on timeout.  Coroutine cancellation propagates immediately —
        no shielded polling or orphaned tasks.
        """
        redis = self._client()
        key = ingestion_ack_key(trace_id)
        deadline = asyncio.get_running_loop().time() + timeout_seconds
        pubsub = redis.pubsub()
        use_pubsub = True
        try:
            # Subscribe before the first level check: a commit landing between
            # check and subscribe is delivered as a message instead of lost.
            try:
                await pubsub.subscribe(TRACE_INGESTED_CHANNEL)
            except Exception:
                use_pubsub = False
                logger.exception(
                    "trace_finalization.subscribe_failed trace_id=%s", trace_id,
                )
            while True:
                if await self._ack_observed(redis, key):
                    return True
                remaining = deadline - asyncio.get_running_loop().time()
                if remaining <= 0:
                    return False
                slice_seconds = min(remaining, _WAKEUP_POLL_SECONDS)
                if use_pubsub:
                    try:
                        # Bounded blocking read: returns None on timeout, so
                        # the loop wakes at most every _WAKEUP_POLL_SECONDS to
                        # re-check the key (message loss / crashed-worker
                        # safety, not polling latency).
                        message = await pubsub.get_message(
                            ignore_subscribe_messages=True,
                            timeout=slice_seconds,
                        )
                    except Exception:
                        use_pubsub = False
                        logger.exception(
                            "trace_finalization.pubsub_failed trace_id=%s",
                            trace_id,
                        )
                        continue
                    if message and message.get("data") == trace_id:
                        # The message is only a wakeup hint (SET and PUBLISH
                        # may ride different pool connections); the key is
                        # the truth.
                        if await self._ack_observed(redis, key):
                            return True
                else:
                    # Redis unreachable for pub/sub: fall back to bounded key
                    # probes so the wait still observes a late ACK.
                    await asyncio.sleep(slice_seconds)
        finally:
            await _close_pubsub(pubsub)

    @staticmethod
    async def _ack_observed(redis: Any, key: str) -> bool:
        try:
            return bool(await redis.get(key))
        except Exception:
            # An unreachable Redis cannot confirm *or* fabricate persistence;
            # the bounded wait degrades to a timeout (truthful unavailability).
            logger.exception("trace_finalization.ack_probe_failed key=%s", key)
            return False


async def _close_pubsub(pubsub: Any) -> None:
    try:
        close = getattr(pubsub, "aclose", None) or pubsub.close
        result = close()
        if asyncio.iscoroutine(result):
            await result
    except Exception:  # noqa: BLE001 — best-effort resource release
        logger.debug("trace_finalization.pubsub_close_failed", exc_info=True)


__all__ = [
    "TRACE_INGESTED_CHANNEL",
    "TRACE_INGESTED_KEY_PREFIX",
    "TraceIngestionFinalizer",
    "ingestion_ack_key",
]
