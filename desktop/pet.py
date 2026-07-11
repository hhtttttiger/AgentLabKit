"""桌宠窗口：无边框、透明背景、置顶、可拖动。"""
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PySide6.QtCore import Qt, Signal


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
        self._press_pos = None  # 按下时的局部坐标（用于判断是否为点击）

        # ── 布局 ──
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignCenter)

        self._character = QLabel("🐱")
        self._character.setAlignment(Qt.AlignCenter)
        self._character.setStyleSheet("font-size: 48px; background: transparent;")
        layout.addWidget(self._character)

        self._hint = QLabel("点击对话")
        self._hint.setAlignment(Qt.AlignCenter)
        self._hint.setStyleSheet("""
            color: #666; font-size: 12px;
            background: rgba(255,255,255,180);
            border-radius: 8px; padding: 2px 6px;
        """)
        layout.addWidget(self._hint)

    def move_to_corner(self):
        from PySide6.QtWidgets import QApplication
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
            # startSystemMove() 让窗口管理器接管拖动，X11/Wayland 通用
            self.startSystemMove()
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._press_pos is not None:
            # 判断是否为点击（几乎没移动）
            delta = event.position().toPoint() - self._press_pos
            if abs(delta.x()) + abs(delta.y()) < 5:
                self.clicked.emit()
            self._press_pos = None
            event.accept()

    # ── 关闭 → 退出整个应用 ──

    def closeEvent(self, event):
        from PySide6.QtWidgets import QApplication
        QApplication.quit()
        event.accept()

    # ── 右键菜单 ──

    def contextMenuEvent(self, event):
        from PySide6.QtWidgets import QMenu, QApplication
        menu = QMenu(self)
        menu.addAction("显示对话", lambda: self.clicked.emit())
        menu.addSeparator()
        menu.addAction("退出", QApplication.quit)
        menu.exec(event.globalPos())
