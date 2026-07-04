from __future__ import annotations

import os
import threading
import time

# 2024-01-01 00:00:00 UTC
_EPOCH = 1704067200000

_lock = threading.Lock()
_worker_id: int = 0
_sequence: int = 0
_last_ts: int = -1


def configure(worker_id: int | None = None) -> None:
    global _worker_id
    if worker_id is not None:
        _worker_id = worker_id & 0x3FF
    else:
        env_val = os.getenv("SNOWFLAKE_WORKER_ID", "")
        _worker_id = int(env_val) & 0x3FF if env_val else 0


def next_id() -> int:
    global _sequence, _last_ts

    with _lock:
        now = _monotonic_ms()

        if now < _last_ts:
            now = _wait_until(_last_ts)
        elif now == _last_ts:
            _sequence = (_sequence + 1) & 0xFFF
            if _sequence == 0:
                now = _wait_until(_last_ts + 1)
        else:
            _sequence = 0

        _last_ts = now
        return ((now - _EPOCH) << 22) | (_worker_id << 12) | _sequence


def _monotonic_ms() -> int:
    return int(time.time() * 1000)


def _wait_until(target_ms: int) -> int:
    while True:
        now = _monotonic_ms()
        if now >= target_ms:
            return now
        time.sleep((target_ms - now) / 1000.0)


# Auto-configure from env on import
configure()
