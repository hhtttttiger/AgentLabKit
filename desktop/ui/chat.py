"""对话面板：气泡消息 + 输入框 + 图片附件。"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea,
    QLineEdit, QPushButton, QLabel, QFrame, QSizePolicy,
    QFileDialog, QMenu,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QPixmap


# ── 消息气泡 ────────────────────────────────────────────────

class ChatBubble(QFrame):
    """单条消息气泡。"""

    def __init__(self, text: str, is_user: bool = True, parent=None):
        super().__init__(parent)

        bg = "#4A90D9" if is_user else "#FFFFFF"
        fg = "white" if is_user else "#333"
        border = "none" if is_user else "1px solid #E0E0E0"

        self.setStyleSheet(f"""
            ChatBubble {{
                background: {bg};
                border: {border};
                border-radius: 12px;
            }}
        """)
        self.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Minimum)

        # 文本标签
        label = QLabel(text)
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        label.setMaximumWidth(340)
        label.setStyleSheet(f"""
            QLabel {{
                color: {fg};
                background: transparent;
                padding: 8px 12px;
                font-size: 14px;
                border: none;
            }}
        """)
        label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)

        # 外层布局：控制对齐
        outer = QHBoxLayout(self)
        outer.setContentsMargins(6, 2, 6, 2)
        if is_user:
            outer.addStretch()
        outer.addWidget(label)
        if not is_user:
            outer.addStretch()


# ── 图片气泡 ─────────────────────────────────────────────────

class ImageBubble(QFrame):
    """图片消息气泡，显示缩略图。"""

    def __init__(self, pixmap: QPixmap, is_user: bool = True, parent=None):
        super().__init__(parent)

        bg = "#4A90D9" if is_user else "#FFFFFF"
        border = "none" if is_user else "1px solid #E0E0E0"

        self.setStyleSheet(f"""
            ImageBubble {{
                background: {bg};
                border: {border};
                border-radius: 12px;
            }}
        """)
        self.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Minimum)

        # 缩略图（最大 280x200）
        thumb = pixmap.scaled(
            280, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation,
        )
        img_label = QLabel()
        img_label.setPixmap(thumb)
        img_label.setStyleSheet("background: transparent; padding: 4px;")
        img_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)

        outer = QHBoxLayout(self)
        outer.setContentsMargins(6, 2, 6, 2)
        if is_user:
            outer.addStretch()
        outer.addWidget(img_label)
        if not is_user:
            outer.addStretch()


# ── 消息行（包含气泡 + 对齐）──────────────────────────────────

class MessageRow(QWidget):
    """一条消息的容器，负责整体对齐。"""

    def __init__(self, text: str, is_user: bool = True, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        bubble = ChatBubble(text, is_user=is_user)

        if is_user:
            layout.addStretch()
            layout.addWidget(bubble)
        else:
            layout.addWidget(bubble)
            layout.addStretch()


# ── 对话面板 ────────────────────────────────────────────────

class ChatPanel(QWidget):
    """对话面板窗口。"""

    message_sent = Signal(str)
    screenshot_requested = Signal()     # 截图识别
    image_selected = Signal(str)        # 图片文件路径

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AgentLabKit 对话")
        self.setMinimumSize(420, 560)
        self.resize(480, 640)
        self._streaming_label: QLabel | None = None  # 流式气泡的文本标签
        self._streaming_text: str = ""                 # 流式累计文本
        self._init_ui()

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── 标题栏 ──
        title_bar = QFrame()
        title_bar.setStyleSheet("background: #2C3E50; padding: 10px;")
        title_bar.setFixedHeight(48)
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(16, 0, 16, 0)

        title = QLabel("💬 AgentLabKit")
        title.setStyleSheet("color: white; font-size: 16px; font-weight: bold;")
        title_layout.addWidget(title)
        title_layout.addStretch()
        root.addWidget(title_bar)

        # ── 消息区域 ──
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet("""
            QScrollArea { background: #F5F5F5; border: none; }
            QScrollBar:vertical { width: 6px; background: transparent; }
            QScrollBar::handle:vertical { background: #CCC; border-radius: 3px; }
        """)

        self._messages_widget = QWidget()
        self._messages_layout = QVBoxLayout(self._messages_widget)
        self._messages_layout.setContentsMargins(12, 12, 12, 12)
        self._messages_layout.setSpacing(8)
        self._messages_layout.addStretch()

        self._scroll.setWidget(self._messages_widget)
        root.addWidget(self._scroll, 1)

        # ── 输入区域 ──
        input_bar = QFrame()
        input_bar.setStyleSheet("background: white; border-top: 1px solid #E0E0E0;")
        input_bar.setFixedHeight(60)
        input_layout = QHBoxLayout(input_bar)
        input_layout.setContentsMargins(12, 10, 12, 10)
        input_layout.setSpacing(8)

        self._input = QLineEdit()
        self._input.setPlaceholderText("输入消息...")
        self._input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #DDD; border-radius: 18px;
                padding: 8px 16px; font-size: 14px; background: #F9F9F9;
            }
            QLineEdit:focus { border-color: #4A90D9; }
        """)
        self._input.returnPressed.connect(self._on_send)
        input_layout.addWidget(self._input, 1)

        # 附件按钮
        self._attach_btn = QPushButton("📎")
        self._attach_btn.setFixedSize(36, 36)
        self._attach_btn.setStyleSheet("""
            QPushButton {
                background: transparent; border: none;
                border-radius: 18px; font-size: 18px;
            }
            QPushButton:hover { background: #F0F0F0; }
        """)
        self._attach_btn.clicked.connect(self._on_attach)
        input_layout.addWidget(self._attach_btn)

        self._send_btn = QPushButton("发送")
        self._send_btn.setFixedSize(60, 36)
        self._send_btn.setStyleSheet("""
            QPushButton {
                background: #4A90D9; color: white; border: none;
                border-radius: 18px; font-size: 14px; font-weight: bold;
            }
            QPushButton:hover { background: #357ABD; }
            QPushButton:pressed { background: #2A6090; }
        """)
        self._send_btn.clicked.connect(self._on_send)
        input_layout.addWidget(self._send_btn)
        root.addWidget(input_bar)

    # ── 公共接口 ──

    def add_message(self, text: str, is_user: bool = True):
        row = MessageRow(text, is_user=is_user)
        self._messages_layout.insertWidget(self._messages_layout.count() - 1, row)
        self._scroll_to_bottom()

    def add_system_message(self, text: str):
        label = QLabel(text)
        label.setAlignment(Qt.AlignCenter)
        label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        label.setWordWrap(True)
        label.setStyleSheet("""
            QLabel {
                color: #999; font-size: 12px;
                background: transparent; padding: 4px 0px;
            }
        """)
        self._messages_layout.insertWidget(self._messages_layout.count() - 1, label)
        self._scroll_to_bottom()

    def set_input_enabled(self, enabled: bool):
        self._input.setEnabled(enabled)
        self._send_btn.setEnabled(enabled)

    # ── 流式消息 ──

    def start_streaming_message(self):
        """创建一个空的 assistant 气泡，准备流式追加文本。"""
        self._streaming_text = ""

        # 创建气泡框架
        bubble = QFrame()
        bubble.setStyleSheet("""
            QFrame {
                background: #FFFFFF;
                border: 1px solid #E0E0E0;
                border-radius: 12px;
            }
        """)
        bubble.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Minimum)

        self._streaming_label = QLabel("▌")  # 光标
        self._streaming_label.setWordWrap(True)
        self._streaming_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self._streaming_label.setMaximumWidth(340)
        self._streaming_label.setStyleSheet("""
            QLabel {
                color: #333;
                background: transparent;
                padding: 8px 12px;
                font-size: 14px;
                border: none;
            }
        """)
        self._streaming_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)

        outer = QHBoxLayout(bubble)
        outer.setContentsMargins(6, 2, 6, 2)
        outer.addWidget(self._streaming_label)
        outer.addStretch()

        # 包装为行
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.addWidget(bubble)
        row_layout.addStretch()

        self._streaming_row = row
        self._messages_layout.insertWidget(self._messages_layout.count() - 1, row)
        self._scroll_to_bottom()

    def append_streaming_text(self, delta: str):
        """追加文本到当前流式气泡。"""
        if self._streaming_label is None:
            return
        self._streaming_text += delta
        self._streaming_label.setText(self._streaming_text + "▌")
        self._scroll_to_bottom()

    def finish_streaming(self):
        """流式结束，移除光标，最终化气泡。"""
        if self._streaming_label is None:
            return
        self._streaming_label.setText(self._streaming_text)
        self._streaming_label = None
        self._streaming_text = ""

    def _scroll_to_bottom(self):
        self._scroll.verticalScrollBar().setValue(
            self._scroll.verticalScrollBar().maximum()
        )

    def _on_send(self):
        text = self._input.text().strip()
        if not text:
            return
        self._input.clear()
        self.add_message(text, is_user=True)
        self.message_sent.emit(text)

    def _on_attach(self):
        """显示附件菜单：截图识别 / 选择图片。"""
        menu = QMenu(self)
        menu.addAction("📷 截图识别", self.screenshot_requested.emit)
        menu.addAction("🖼️ 选择图片", self._pick_image)
        menu.exec(self._attach_btn.mapToGlobal(
            self._attach_btn.rect().bottomLeft()
        ))

    def _pick_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择图片", "",
            "图片 (*.png *.jpg *.jpeg *.gif *.bmp *.webp);;所有文件 (*)",
        )
        if path:
            self.image_selected.emit(path)

    def add_image_message(self, pixmap: QPixmap, is_user: bool = True):
        """添加图片消息气泡。"""
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        bubble = ImageBubble(pixmap, is_user=is_user)
        if is_user:
            layout.addStretch()
            layout.addWidget(bubble)
        else:
            layout.addWidget(bubble)
            layout.addStretch()
        self._messages_layout.insertWidget(self._messages_layout.count() - 1, row)
        self._scroll_to_bottom()
