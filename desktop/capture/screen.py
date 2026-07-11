"""截图 + 区域选择：全屏覆盖层，鼠标框选区域。

使用 PySide6 原生能力，无需 Pillow。
"""
from __future__ import annotations

from PySide6.QtWidgets import QWidget, QApplication
from PySide6.QtCore import Qt, QRect, QPoint, Signal
from PySide6.QtGui import QPainter, QColor, QPen, QCursor, QPixmap


class ScreenOverlay(QWidget):
    """全屏半透明覆盖层，鼠标框选截图区域。

    完成后发射 region_selected(QPixmap) 或 region_cancelled()。
    """

    region_selected = Signal(QPixmap)
    region_cancelled = Signal()

    def __init__(self, screen_pixmap: QPixmap, parent=None):
        super().__init__(parent)
        self._pixmap = screen_pixmap
        self._origin = QPoint()
        self._selection = QRect()
        self._selecting = False

        # 全屏无边框 + 置顶
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )
        self.setCursor(QCursor(Qt.CrossCursor))
        self.setGeometry(QApplication.primaryScreen().geometry())

    def paintEvent(self, event):
        painter = QPainter(self)
        # 画截图底图
        painter.drawPixmap(0, 0, self._pixmap)

        # 半透明遮罩
        overlay = QColor(0, 0, 0, 100)
        painter.fillRect(self.rect(), overlay)

        # 选区内显示原图（清除遮罩）
        if not self._selection.isNull():
            painter.setClipRect(self._selection)
            painter.drawPixmap(0, 0, self._pixmap)
            painter.setClipping(False)

            # 选区边框
            pen = QPen(QColor("#4A90D9"), 2, Qt.SolidLine)
            painter.setPen(pen)
            painter.drawRect(self._selection)

            # 尺寸提示
            size_text = f"{self._selection.width()} × {self._selection.height()}"
            painter.setPen(QColor("white"))
            painter.setFont(painter.font())
            text_rect = painter.boundingRect(
                self._selection.topLeft().x(),
                self._selection.topLeft().y() - 20,
                200, 20, 0, size_text,
            )
            painter.fillRect(text_rect.adjusted(-4, -2, 4, 2), QColor(0, 0, 0, 160))
            painter.drawText(text_rect, 0, size_text)

        painter.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._origin = event.position().toPoint()
            self._selection = QRect(self._origin, self._origin)
            self._selecting = True

    def mouseMoveEvent(self, event):
        if self._selecting:
            self._selection = QRect(self._origin, event.position().toPoint()).normalized()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._selecting:
            self._selecting = False
            self._selection = QRect(self._origin, event.position().toPoint()).normalized()

            # 最小尺寸检查（太小视为取消）
            if self._selection.width() < 10 or self._selection.height() < 10:
                self.region_cancelled.emit()
            else:
                cropped = self._pixmap.copy(self._selection)
                self.region_selected.emit(cropped)
            self.close()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.region_cancelled.emit()
            self.close()


def capture_screen_region() -> tuple[ScreenOverlay, QPixmap]:
    """截取全屏并显示区域选择覆盖层。

    Returns:
        (overlay, full_pixmap) — overlay 需要 show()，连接信号后使用。
    """
    screen = QApplication.primaryScreen()
    if not screen:
        raise RuntimeError("No screen available")
    pixmap = screen.grabWindow(0)
    overlay = ScreenOverlay(pixmap)
    return overlay, pixmap
