"""设置面板：LLM 提供商配置。"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QComboBox, QLineEdit, QPushButton, QLabel, QFrame,
    QGroupBox, QMessageBox, QSizePolicy,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from core.config import AppConfig, LLMConfig


# ── 提供商预设 ─────────────────────────────────────────────────

PRESETS = {
    "OpenAI": {
        "provider": "openai",
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
    },
    "Anthropic": {
        "provider": "anthropic",
        "base_url": "https://api.anthropic.com/v1",
        "model": "claude-sonnet-4-20250514",
    },
    "DeepSeek": {
        "provider": "openai",
        "base_url": "https://api.deepseek.com/v1",
        "model": "deepseek-chat",
    },
    "Ollama (本地)": {
        "provider": "openai",
        "base_url": "http://localhost:11434/v1",
        "model": "qwen2.5:7b",
    },
    "自定义": {
        "provider": "openai",
        "base_url": "",
        "model": "",
    },
}


class SettingsDialog(QDialog):
    """设置对话框。"""

    settings_saved = Signal(AppConfig)  # 保存后发射新配置

    def __init__(self, config: AppConfig, parent=None):
        super().__init__(parent)
        self._config = config
        self.setWindowTitle("⚙️ 设置")
        self.setMinimumWidth(460)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self._init_ui()
        self._load_current()

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(16)

        # ── 标题 ──
        title = QLabel("LLM 提供商配置")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #2C3E50;")
        root.addWidget(title)

        # ── 预设选择 ──
        preset_group = QGroupBox("快速选择")
        preset_layout = QHBoxLayout(preset_group)
        for name in PRESETS:
            btn = QPushButton(name)
            btn.setStyleSheet("""
                QPushButton {
                    background: #ECF0F1; border: 1px solid #BDC3C7;
                    border-radius: 6px; padding: 6px 12px; font-size: 13px;
                }
                QPushButton:hover { background: #D5DBDB; }
                QPushButton:pressed { background: #BDC3C7; }
            """)
            btn.clicked.connect(lambda checked, n=name: self._apply_preset(n))
            preset_layout.addWidget(btn)
        root.addWidget(preset_group)

        # ── 表单 ──
        form_group = QGroupBox("详细配置")
        form = QFormLayout(form_group)
        form.setSpacing(10)

        self._provider_combo = QComboBox()
        self._provider_combo.addItems(["openai", "anthropic"])
        self._provider_combo.setToolTip("API 协议类型（Ollama 使用 openai 兼容模式）")
        form.addRow("协议类型：", self._provider_combo)

        self._url_input = QLineEdit()
        self._url_input.setPlaceholderText("https://api.openai.com/v1")
        form.addRow("Base URL：", self._url_input)

        self._key_input = QLineEdit()
        self._key_input.setEchoMode(QLineEdit.Password)
        self._key_input.setPlaceholderText("sk-...")
        # 显示/隐藏按钮
        key_row = QHBoxLayout()
        key_row.addWidget(self._key_input, 1)
        self._toggle_btn = QPushButton("👁")
        self._toggle_btn.setFixedSize(32, 32)
        self._toggle_btn.setStyleSheet("""
            QPushButton {
                background: transparent; border: none; font-size: 16px;
            }
            QPushButton:hover { background: #F0F0F0; border-radius: 4px; }
        """)
        self._toggle_btn.clicked.connect(self._toggle_key_visibility)
        key_row.addWidget(self._toggle_btn)
        form.addRow("API Key：", key_row)

        self._model_input = QLineEdit()
        self._model_input.setPlaceholderText("gpt-4o-mini")
        form.addRow("模型：", self._model_input)

        root.addWidget(form_group)

        # ── 状态标签 ──
        self._status = QLabel("")
        self._status.setStyleSheet("color: #E74C3C; font-size: 12px;")
        self._status.setWordWrap(True)
        root.addWidget(self._status)

        # ── 按钮 ──
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedSize(80, 32)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: #ECF0F1; border: 1px solid #BDC3C7;
                border-radius: 6px; font-size: 14px;
            }
            QPushButton:hover { background: #D5DBDB; }
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        save_btn = QPushButton("保存")
        save_btn.setFixedSize(80, 32)
        save_btn.setStyleSheet("""
            QPushButton {
                background: #4A90D9; color: white; border: none;
                border-radius: 6px; font-size: 14px; font-weight: bold;
            }
            QPushButton:hover { background: #357ABD; }
            QPushButton:pressed { background: #2A6090; }
        """)
        save_btn.clicked.connect(self._on_save)
        btn_row.addWidget(save_btn)

        root.addLayout(btn_row)

    def _load_current(self):
        """从当前配置加载值。"""
        llm = self._config.llm
        idx = self._provider_combo.findText(llm.provider)
        if idx >= 0:
            self._provider_combo.setCurrentIndex(idx)
        self._url_input.setText(llm.base_url)
        self._key_input.setText(llm.api_key)
        self._model_input.setText(llm.model)

    def _apply_preset(self, name: str):
        """应用预设。"""
        preset = PRESETS[name]
        idx = self._provider_combo.findText(preset["provider"])
        if idx >= 0:
            self._provider_combo.setCurrentIndex(idx)
        if preset["base_url"]:
            self._url_input.setText(preset["base_url"])
        if preset["model"]:
            self._model_input.setText(preset["model"])
        self._key_input.setFocus()
        self._status.setText(f"已选择 {name} 预设，请填写 API Key")
        self._status.setStyleSheet("color: #3498DB; font-size: 12px;")

    def _toggle_key_visibility(self):
        if self._key_input.echoMode() == QLineEdit.Password:
            self._key_input.setEchoMode(QLineEdit.Normal)
            self._toggle_btn.setText("🙈")
        else:
            self._key_input.setEchoMode(QLineEdit.Password)
            self._toggle_btn.setText("👁")

    def _on_save(self):
        """验证并保存。"""
        provider = self._provider_combo.currentText()
        base_url = self._url_input.text().strip()
        api_key = self._key_input.text().strip()
        model = self._model_input.text().strip()

        if not base_url:
            self._status.setText("请填写 Base URL")
            self._status.setStyleSheet("color: #E74C3C; font-size: 12px;")
            return
        if not model:
            self._status.setText("请填写模型名称")
            self._status.setStyleSheet("color: #E74C3C; font-size: 12px;")
            return

        # 构建新配置
        new_config = AppConfig(
            llm=LLMConfig(
                provider=provider,
                base_url=base_url,
                api_key=api_key,
                model=model,
            )
        )
        new_config.save()
        self._status.setText("✅ 已保存")
        self._status.setStyleSheet("color: #27AE60; font-size: 12px;")
        self.settings_saved.emit(new_config)
        self.accept()

    @property
    def config(self) -> AppConfig:
        return AppConfig(
            llm=LLMConfig(
                provider=self._provider_combo.currentText(),
                base_url=self._url_input.text().strip(),
                api_key=self._key_input.text().strip(),
                model=self._model_input.text().strip(),
            )
        )
