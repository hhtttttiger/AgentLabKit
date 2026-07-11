"""全局快捷键监听。

使用 pynput 在后台线程监听系统级热键，默认 Ctrl+Space 唤起对话面板。
pynput 不可用时降级为无操作（日志提示）。
"""
from __future__ import annotations

import logging
import threading
from typing import Callable

logger = logging.getLogger("desktop.hotkey")

# 默认快捷键
DEFAULT_COMBO = "<ctrl>+<space>"


class GlobalHotkey:
    """全局快捷键监听器。"""

    def __init__(self, combo: str = DEFAULT_COMBO, callback: Callable[[], None] | None = None):
        self._combo = combo
        self._callback = callback
        self._listener = None
        self._thread = None
        self._available = False

    def start(self) -> bool:
        """启动监听，返回是否成功。"""
        try:
            from pynput import keyboard
        except ImportError:
            logger.warning("pynput 未安装，全局快捷键不可用。安装：pip install pynput")
            return False

        def _on_activate():
            logger.info(f"Hotkey activated: {self._combo}")
            if self._callback:
                self._callback()

        try:
            hotkey = keyboard.HotKey(
                keyboard.HotKey.parse(self._combo),
                _on_activate,
            )

            def _for_canonical(listener):
                """将按键事件转为规范形式后传给 HotKey。"""
                def canonical(key):
                    try:
                        hotkey.press(listener.canonical(key))
                    except Exception:
                        pass
                return canonical

            self._listener = keyboard.Listener(
                on_press=_for_canonical(None),  # 占位，下面替换
                on_release=lambda key: None,
            )
            # 正确设置 canonical
            self._listener.on_press = _for_canonical(self._listener)

            self._listener.start()
            self._available = True
            logger.info(f"Global hotkey registered: {self._combo}")
            return True

        except Exception as e:
            logger.warning(f"Failed to register hotkey: {e}")
            return False

    def stop(self):
        if self._listener:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None

    @property
    def available(self) -> bool:
        return self._available
