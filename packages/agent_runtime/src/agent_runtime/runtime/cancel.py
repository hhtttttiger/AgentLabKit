"""Cancellation support for agent runs — Python equivalent of AbortController/AbortSignal.

Provides :class:`CancelToken` (the signal) and :class:`CancelScope` (the
controller). The token can be passed through the call stack so that any layer
can cooperatively check for cancellation.
"""

from __future__ import annotations

import asyncio
from types import TracebackType


class CancelToken:
    """Cooperative cancellation token — Python version of ``AbortSignal``.

    Usage::

        token = CancelToken()
        token.check()              # raises CancelledError if cancelled
        await token.race(some_coroutine)  # cancels on token.cancel()
    """

    def __init__(self) -> None:
        self._event: asyncio.Event = asyncio.Event()

    # ── Status ────────────────────────────────────────────────────────────

    @property
    def is_cancelled(self) -> bool:
        return self._event.is_set()

    # ── Trigger ───────────────────────────────────────────────────────────

    def cancel(self) -> None:
        """Mark this token as cancelled."""
        self._event.set()

    # ── Check helpers ─────────────────────────────────────────────────────

    def check(self) -> None:
        """Raise :class:`asyncio.CancelledError` if cancelled.

        Call this in synchronous code paths (e.g. between ``await`` points)
        to cooperatively abort.
        """
        if self._event.is_set():
            raise asyncio.CancelledError("Agent run was cancelled")

    async def wait_cancelled(self) -> None:
        """Block until cancelled."""
        await self._event.wait()

    async def race(self, coro: asyncio.coroutines) -> Any:  # type: ignore[type-arg]
        """Await *coro* but cancel early if this token is triggered.

        Returns the coroutine result, or raises ``CancelledError`` if the
        token fires first.
        """
        task = asyncio.ensure_future(coro)
        wait_task = asyncio.ensure_future(self._event.wait())
        done, pending = await asyncio.wait(
            {task, wait_task},
            return_when=asyncio.FIRST_COMPLETED,
        )
        for p in pending:
            p.cancel()
            try:
                await p
            except (asyncio.CancelledError, Exception):
                pass
        if wait_task in done:
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass
            raise asyncio.CancelledError("Agent run was cancelled")
        return task.result()


class CancelScope:
    """Context manager that owns a :class:`CancelToken` — Python ``AbortController``.

    Usage::

        scope = CancelScope()
        async with scope:
            await run_agent_loop(..., cancel_token=scope.token)
        # scope.token is not cancelled here

        # To cancel:
        scope.cancel()
    """

    def __init__(self) -> None:
        self.token = CancelToken()

    def cancel(self) -> None:
        self.token.cancel()

    async def __aenter__(self) -> CancelToken:
        return self.token

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool:
        return False


__all__ = ["CancelScope", "CancelToken"]
