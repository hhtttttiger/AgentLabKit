"""系统托盘：图标 + 右键菜单。"""
from PySide6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont
from PySide6.QtCore import Signal, QObject


def _create_placeholder_icon() -> QIcon:
    """生成一个占位图标（后续替换为正式图标）。"""
    size = 64
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor(0, 0, 0, 0))  # 透明

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    # 圆形背景
    painter.setBrush(QColor("#4A90D9"))
    painter.setPen(QColor("#4A90D9"))
    painter.drawEllipse(4, 4, size - 8, size - 8)

    # 文字
    painter.setPen(QColor("white"))
    painter.setFont(QFont("Sans", 28, QFont.Bold))
    painter.drawText(pixmap.rect(), 0x0084, "A")  # AlignCenter

    painter.end()
    return QIcon(pixmap)


class TrayManager(QObject):
    """系统托盘管理器。"""

    # 信号
    show_chat_requested = Signal()
    settings_requested = Signal()
    quit_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self._tray = QSystemTrayIcon(_create_placeholder_icon(), parent)
        self._tray.setToolTip("AgentLabKit")

        # ── 右键菜单 ──
        menu = QMenu()
        menu.addAction("💬 显示对话", self.show_chat_requested.emit)
        menu.addSeparator()
        menu.addAction("⚙️ 设置", self.settings_requested.emit)
        menu.addSeparator()
        menu.addAction("❌ 退出", self.quit_requested.emit)
        self._tray.setContextMenu(menu)

        # 单击托盘图标 → 显示对话
        self._tray.activated.connect(self._on_activated)

    @property
    def available(self) -> bool:
        """托盘是否可用（WSLg 下可能不支持）。"""
        return QSystemTrayIcon.isSystemTrayAvailable()

    def show(self):
        if self.available:
            self._tray.show()
        else:
            print("[tray] 系统托盘不可用（WSLg 下 StatusNotifierWatcher 缺失，跳过）")

    def hide(self):
        self._tray.hide()

    def _on_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            self.show_chat_requested.emit()

