"""剪贴板监听：检测剪贴板变化，发射信号。

使用 QTimer 轮询 QClipboard（Qt 原生，跨平台）。
"""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal, QTimer
from PySide6.QtWidgets import QApplication


class ClipboardWatcher(QObject):
    """剪贴板变化监听器。"""

    text_copied = Signal(str)  # 新文本被复制时发射

    def __init__(self, interval_ms: int = 1000, parent=None):
        super().__init__(parent)
        self._last_text = ""
        self._enabled = True

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._check)
        self._timer.start(interval_ms)

    def _check(self):
        if not self._enabled:
            return
        clipboard = QApplication.clipboard()
        if clipboard is None:
            return
        text = clipboard.text()
        if text and text != self._last_text:
            self._last_text = text
            self.text_copied.emit(text)

    def set_enabled(self, enabled: bool):
        self._enabled = enabled

    def stop(self):
        self._timer.stop()
