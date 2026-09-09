"""Cancellation never leaves model/tool work running outside its caller."""
import asyncio

import pytest

from agent_runtime.runtime.cancel import CancelToken


@pytest.mark.asyncio
@pytest.mark.parametrize("cancel_source", ["task", "token"])
async def test_cancel_joins_inflight_operation(cancel_source):
    token = CancelToken()
    entered = asyncio.Event()
    cleaned = asyncio.Event()
    before = asyncio.all_tasks()

    async def operation():
        try:
            entered.set()
            await asyncio.Event().wait()
        finally:
            await asyncio.sleep(0)
            cleaned.set()

    caller = asyncio.create_task(token.race(operation()))
    await entered.wait()
    if cancel_source == "task":
        caller.cancel()
    else:
        token.cancel()
    with pytest.raises(asyncio.CancelledError):
        await caller

    assert cleaned.is_set()
    assert not (asyncio.all_tasks() - before)


@pytest.mark.asyncio
@pytest.mark.parametrize("fails", [False, True])
async def test_operation_completion_preserves_result_and_cleans_waiter(fails):
    token = CancelToken()
    before = asyncio.all_tasks()

    async def operation():
        if fails:
            raise ValueError("provider failed")
        return "reply"

    if fails:
        with pytest.raises(ValueError, match="provider failed"):
            await token.race(operation())
    else:
        assert await token.race(operation()) == "reply"
    assert not token.is_cancelled
    assert not (asyncio.all_tasks() - before)
