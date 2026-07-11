"""异步桥接：在 PySide6 的 Qt 事件循环中运行 asyncio 协程。

PySide6 和 asyncio 各有自己的事件循环，不能直接嵌套。
解决方案：在独立 QThread 中运行 asyncio 事件循环，
通过 Signal 将结果传回 Qt 主线程。
"""
from __future__ import annotations

import asyncio
from typing import Any, Callable

from PySide6.QtCore import QThread, Signal, QObject


class _AsyncThread(QThread):
    """后台线程，运行独立的 asyncio 事件循环。"""

    result_ready = Signal(object)  # 协程结果
    error_ready = Signal(object)   # 协程异常

    def __init__(self, coro, parent=None):
        super().__init__(parent)
        self._coro = coro

    def run(self):
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(self._coro)
            self.result_ready.emit(result)
        except Exception as e:
            self.error_ready.emit(e)
        finally:
            loop.close()


def run_async(
    coro,
    on_result: Callable[[Any], None] | None = None,
    on_error: Callable[[Exception], None] | None = None,
    parent: QObject | None = None,
) -> _AsyncThread:
    """在后台线程运行 asyncio 协程，结果通过回调返回 Qt 主线程。

    Usage:
        run_async(
            gateway.generate_text(request),
            on_result=lambda resp: print(resp.text),
            on_error=lambda e: print(f"Error: {e}"),
        )
    """
    thread = _AsyncThread(coro, parent=parent)
    if on_result:
        thread.result_ready.connect(on_result)
    if on_error:
        thread.error_ready.connect(on_error)
    thread.finished.connect(thread.deleteLater)
    thread.start()
    return thread


# ── 流式支持 ───────────────────────────────────────────────────

class _AsyncStreamThread(QThread):
    """后台线程，迭代 async generator，逐个事件传回 Qt 主线程。"""

    event_ready = Signal(object)   # 每个事件
    finished_ready = Signal()      # 完成
    error_ready = Signal(object)   # 异常

    def __init__(self, agen_factory, parent=None):
        """agen_factory: 无参函数，返回 async generator。"""
        super().__init__(parent)
        self._agen_factory = agen_factory

    def run(self):
        loop = asyncio.new_event_loop()
        try:
            async def consume():
                async for event in self._agen_factory():
                    self.event_ready.emit(event)
            loop.run_until_complete(consume())
            self.finished_ready.emit()
        except Exception as e:
            self.error_ready.emit(e)
        finally:
            loop.close()


def run_async_stream(
    agen_factory,
    on_event: Callable[[Any], None] | None = None,
    on_done: Callable[[], None] | None = None,
    on_error: Callable[[Exception], None] | None = None,
    parent: QObject | None = None,
) -> _AsyncStreamThread:
    """在后台线程迭代 async generator，每个事件通过回调返回 Qt 主线程。

    Args:
        agen_factory: 无参函数，返回 async generator（如 lambda: runtime.stream_turn(req)）
        on_event: 每收到一个事件时回调
        on_done: generator 迭代完成时回调
        on_error: 异常时回调

    Usage:
        run_async_stream(
            lambda: self._agent.runtime.stream_turn(request),
            on_event=lambda ev: handle_stream_event(ev),
            on_done=lambda: print("done"),
            on_error=lambda e: print(f"Error: {e}"),
        )
    """
    thread = _AsyncStreamThread(agen_factory, parent=parent)
    if on_event:
        thread.event_ready.connect(on_event)
    if on_done:
        thread.finished_ready.connect(on_done)
    if on_error:
        thread.error_ready.connect(on_error)
    thread.finished.connect(thread.deleteLater)
    thread.start()
    return thread
