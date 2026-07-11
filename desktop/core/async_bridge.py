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
