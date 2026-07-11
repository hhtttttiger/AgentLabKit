"""桌宠窗口：无边框、透明背景、置顶、可拖动。

支持动画状态：idle（眨眼）、thinking（等待）、happy（反应）。
"""
from __future__ import annotations

import random
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QMenu, QApplication
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QCursor


# ── 动画帧定义 ────────────────────────────────────────────────

ANIM_IDLE = ["🐱", "😺", "🐱", "😸"]          # 眨眼循环
ANIM_THINKING = ["🐱", "🤔", "🐱", "💭"]       # 思考中
ANIM_HAPPY = ["😻", "🥰", "😻", "💕"]          # 开心
ANIM_SLEEPY = ["🐱", "😴", "💤", "😴"]         # 困了


class PetWindow(QWidget):
    """桌宠主窗口。"""

    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(120, 140)

        # ── 拖动状态 ──
        self._press_pos = None

        # ── 动画状态 ──
        self._anim_frames = ANIM_IDLE
        self._anim_index = 0
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._next_frame)
        self._anim_timer.start(800)  # 800ms 一帧

        # ── 空闲计时（长时间无交互 → 困了）──
        self._idle_count = 0
        self._idle_timer = QTimer(self)
        self._idle_timer.timeout.connect(self._on_idle_tick)
        self._idle_timer.start(30_000)  # 30 秒检查一次

        # ── 布局 ──
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignCenter)

        self._character = QLabel("🐱")
        self._character.setAlignment(Qt.AlignCenter)
        self._character.setStyleSheet("font-size: 48px; background: transparent;")
        layout.addWidget(self._character)

        self._status = QLabel("")
        self._status.setAlignment(Qt.AlignCenter)
        self._status.setStyleSheet("""
            color: #666; font-size: 11px;
            background: rgba(255,255,255,180);
            border-radius: 8px; padding: 2px 6px;
        """)
        self._status.hide()
        layout.addWidget(self._status)

    # ── 动画控制 ──

    def set_state(self, state: str):
        """切换动画状态：'idle' | 'thinking' | 'happy' | 'sleepy'"""
        state_map = {
            "idle": ANIM_IDLE,
            "thinking": ANIM_THINKING,
            "happy": ANIM_HAPPY,
            "sleepy": ANIM_SLEEPY,
        }
        self._anim_frames = state_map.get(state, ANIM_IDLE)
        self._anim_index = 0
        self._idle_count = 0  # 任何状态切换都重置空闲计数

    def show_status(self, text: str, duration: int = 3000):
        """显示临时状态文字。"""
        self._status.setText(text)
        self._status.show()
        QTimer.singleShot(duration, self._status.hide)

    def _next_frame(self):
        """播放下一帧动画。"""
        self._anim_index = (self._anim_index + 1) % len(self._anim_frames)
        self._character.setText(self._anim_frames[self._anim_index])

    def _on_idle_tick(self):
        """空闲计时：长时间无交互 → 困了。"""
        self._idle_count += 1
        if self._idle_count >= 4:  # 2 分钟无交互
            self.set_state("sleepy")
            self.show_status("好困...", 5000)

    def poke(self):
        """戳一下桌宠（外部调用）。"""
        self.set_state("happy")
        self.show_status("嘿嘿~", 2000)

    def think(self):
        """进入思考状态（LLM 请求中）。"""
        self.set_state("thinking")
        self.show_status("思考中...", 10000)

    def done(self):
        """回到 idle。"""
        self.set_state("idle")

    # ── 位置 ──

    def move_to_corner(self):
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            self.move(
                geo.x() + geo.width() - self.width() - 40,
                geo.y() + geo.height() - self.height() - 80,
            )

    # ── 鼠标事件（Wayland 兼容）──

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._press_pos = event.position().toPoint()
            self.startSystemMove()
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._press_pos is not None:
            delta = event.position().toPoint() - self._press_pos
            if abs(delta.x()) + abs(delta.y()) < 5:
                self.poke()
                self.clicked.emit()
            self._press_pos = None
            event.accept()

    # ── 关闭 → 退出整个应用 ──

    def closeEvent(self, event):
        QApplication.quit()
        event.accept()

    # ── 右键菜单 ──

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.addAction("💬 显示对话", lambda: self.clicked.emit())
        menu.addSeparator()
        menu.addAction("🐟 喂鱼", lambda: self._react("🐟", "好好吃！"))
        menu.addAction("✋ 摸摸头", lambda: self._react("🥰", "开心~"))
        menu.addAction("🎾 玩耍", lambda: self._react("🎾", "嘿嘿！"))
        menu.addSeparator()
        menu.addAction("❌ 退出", QApplication.quit)
        menu.exec(event.globalPos())

    def _react(self, emoji: str, text: str):
        """右键菜单互动反应。"""
        self.set_state("happy")
        self.show_status(f"{emoji} {text}", 2000)
