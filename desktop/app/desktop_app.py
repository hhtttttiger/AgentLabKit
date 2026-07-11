"""AgentLabKit Desktop — 主控制器。

整合桌宠、托盘、对话面板、Agent Runtime、聊天历史持久化。
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPixmap

from core.config import AppConfig, CONFIG_FILE
from core.bootstrap import create_agent
from core.async_bridge import run_async, run_async_stream
from ui.pet import PetWindow
from ui.tray import TrayManager
from ui.chat import ChatPanel
from ui.settings import SettingsDialog
from storage.chat_store import ChatStore
from capture.screen import capture_screen_region
from capture.vision import analyze_image, pixmap_to_base64
from utils.hotkey import GlobalHotkey
from utils.clipboard import ClipboardWatcher
from tools.registry import create_desktop_tool_registry
from agent_runtime import (
    AgentModule,
    AgentTurnRequest,
    AgentTurnStreamEvent,
    AgentMessage,
    AgentRole,
)

# ── 日志 ──
LOG_FILE = Path.home() / ".config" / "agentlabkit" / "desktop.log"
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("desktop")


class DesktopApp:
    """桌面应用主控制器。"""

    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)
        self._quitting = False

        # ── 配置 ──
        self.config = AppConfig.load()
        logger.info(f"Config: provider={self.config.llm.provider}, model={self.config.llm.model}")
        self._agent: AgentModule | None = None

        # ── 聊天存储 ──
        self._store = ChatStore()

        # ── 对话面板 ──
        self.chat = ChatPanel()
        self.chat.message_sent.connect(self._on_message_sent)
        self.chat.screenshot_requested.connect(self._on_screenshot)
        self.chat.image_selected.connect(self._on_image_file)

        # ── 恢复历史 ──
        self._load_history()

        # ── 桌宠 ──
        self.pet = PetWindow()
        self.pet.clicked.connect(self._toggle_chat)
        self.pet.show()
        self.pet.move_to_corner()

        # ── 托盘 ──
        self.tray = TrayManager()
        self.tray.show_chat_requested.connect(self._toggle_chat)
        self.tray.settings_requested.connect(self._show_settings)
        self.tray.quit_requested.connect(self._quit)
        self.tray.show()

        # ── Agent ──
        self._init_agent()

        # ── 全局快捷键 ──
        self._hotkey = GlobalHotkey(callback=self._toggle_chat)
        if self._hotkey.start():
            logger.info("Global hotkey: Ctrl+Space")
        else:
            logger.info("Global hotkey unavailable (pynput not installed)")

        # ── 剪贴板监听 ──
        self._clipboard = ClipboardWatcher(parent=self.app)
        self._clipboard.text_copied.connect(self._on_clipboard_text)

        # ── 应用退出信号 ──
        self.app.aboutToQuit.connect(self._cleanup)

    def _load_history(self):
        messages = self._store.recent(limit=50)
        if messages:
            for msg in messages:
                if msg.role == "user":
                    self.chat.add_message(msg.content, is_user=True)
                elif msg.role == "assistant":
                    self.chat.add_message(msg.content, is_user=False)

    def _init_agent(self):
        llm = self.config.llm
        if not llm.api_key:
            self.chat.add_system_message(f"⚠️ 未配置 API Key，请编辑：\n{CONFIG_FILE}")
            return
        try:
            tool_registry = create_desktop_tool_registry()
            self._agent = create_agent(llm, tool_registry=tool_registry)
            self.chat.add_system_message(f"已连接 {llm.provider}（{llm.model}），Agent 就绪")
            logger.info("Agent initialized")
        except Exception as e:
            self.chat.add_system_message(f"⚠️ 连接失败：{e}")
            logger.exception("Agent init failed")

    def run(self) -> int:
        return self.app.exec()

    def _toggle_chat(self):
        if self.chat.isVisible():
            self.chat.hide()
        else:
            self.chat.show()
            self.chat.activateWindow()
            self.chat.raise_()

    def _show_settings(self):
        """打开设置面板，保存后重新初始化 Agent。"""
        dialog = SettingsDialog(self.config, parent=self.chat)
        if dialog.exec() == SettingsDialog.Accepted:
            new_config = dialog.config
            self.config = new_config
            logger.info(f"Settings changed: provider={new_config.llm.provider}, model={new_config.llm.model}")
            self._reinit_agent()

    def _reinit_agent(self):
        """重新初始化 Agent（配置变更后）。"""
        self._agent = None
        self.chat.add_system_message("⚙️ 配置已更新，正在重新连接...")
        self._init_agent()

    # ── 消息处理（Agent Runtime）──

    def _build_history(self) -> list[AgentMessage]:
        """从 ChatStore 构建 agent_runtime 的 AgentMessage 列表。"""
        messages = self._store.recent(limit=50)
        history = []
        for msg in messages:
            role_map = {
                "user": AgentRole.USER,
                "assistant": AgentRole.ASSISTANT,
                "system": AgentRole.SYSTEM,
            }
            role = role_map.get(msg.role)
            if role:
                history.append(AgentMessage(role=role, content=msg.content))
        return history

    def _on_message_sent(self, text: str):
        if not self._agent:
            self.chat.add_system_message("⚠️ Agent 未连接，请检查配置")
            return

        self._store.add("user", text)
        self.chat.set_input_enabled(False)
        self.chat.start_streaming_message()
        self.pet.think()
        logger.info(f"Sending: {text[:80]}...")

        request = AgentTurnRequest(
            session_id="desktop",
            user_message=text,
            history=self._build_history(),
        )

        run_async_stream(
            lambda: self._agent.runtime.stream_turn(request),
            on_event=self._on_stream_event,
            on_done=self._on_stream_done,
            on_error=self._on_stream_error,
            parent=self.chat,
        )

    def _on_stream_event(self, event: AgentTurnStreamEvent):
        """处理流式事件。"""
        if event.event_type == "reply_delta":
            self.chat.append_streaming_text(event.delta or "")
        elif event.event_type == "tool_call":
            name = event.tool_name or "?"
            self.chat.append_streaming_text(f"\n\n🔧 *调用工具: {name}*")
            logger.info(f"Tool call: {name}")
        elif event.event_type == "tool_result":
            name = event.tool_name or "?"
            # 工具结果不直接显示在流式气泡中（太长），只记录日志
            if event.tool_event:
                output = event.tool_event.output or ""
                logger.info(f"Tool result [{name}]: {output[:200]}")
        elif event.event_type == "reply_completed":
            # 流式完成，保存最终文本
            text = event.reply_text or ""
            if text:
                self._store.add("assistant", text)
            logger.info(f"Reply completed: {text[:80]}...")
        elif event.event_type == "error":
            error = event.error
            msg = f"❌ {error.code}: {error.message}" if error else "❌ 未知错误"
            self.chat.finish_streaming()
            self.chat.add_system_message(msg)
            logger.error(f"Stream error: {error}")

    def _on_stream_done(self):
        """流式完成。"""
        self.chat.finish_streaming()
        self.chat.set_input_enabled(True)
        self.pet.done()

    def _on_stream_error(self, error: Exception):
        """流式异常。"""
        self.chat.finish_streaming()
        msg = f"❌ 请求失败：{type(error).__name__}: {error}"
        self.chat.add_system_message(msg)
        logger.exception("Stream error")
        self.chat.set_input_enabled(True)
        self.pet.done()

    # ── 图片理解（直连 Vision API，不走 Agent）──

    def _on_screenshot(self):
        """截图识别：隐藏窗口 → 全屏覆盖 → 框选 → 分析。"""
        self.chat.hide()
        self.pet.hide()

        from PySide6.QtCore import QTimer
        QTimer.singleShot(150, self._do_capture)

    def _do_capture(self):
        try:
            overlay, _ = capture_screen_region()
            overlay.region_selected.connect(self._on_region_selected)
            overlay.region_cancelled.connect(self._on_capture_cancelled)
            overlay.show()
            self._overlay = overlay
        except Exception as e:
            logger.exception("Capture failed")
            self.chat.add_system_message(f"❌ 截图失败：{e}")
            self.chat.show()

    def _on_region_selected(self, pixmap):
        self._overlay = None
        self.chat.show()
        self.pet.show()

        self.chat.add_image_message(pixmap, is_user=True)
        self._analyze_pixmap(pixmap)

    def _on_capture_cancelled(self):
        self._overlay = None
        self.chat.show()
        self.pet.show()
        self.chat.add_system_message("已取消截图")

    def _on_image_file(self, path: str):
        pixmap = QPixmap(path)
        if pixmap.isNull():
            self.chat.add_system_message(f"❌ 无法加载图片：{path}")
            return
        self.chat.add_image_message(pixmap, is_user=True)
        self._analyze_pixmap(pixmap)

    def _analyze_pixmap(self, pixmap):
        if not self.config.llm.api_key:
            self.chat.add_system_message("⚠️ 未配置 API Key，无法分析图片")
            return

        self.chat.set_input_enabled(False)
        self.chat.add_system_message("🔍 正在分析图片...")

        image_b64 = pixmap_to_base64(pixmap)
        run_async(
            analyze_image(self.config.llm, image_b64),
            on_result=self._on_vision_response,
            on_error=self._on_vision_error,
            parent=self.chat,
        )

    def _on_vision_response(self, text: str):
        self.chat.add_message(text, is_user=False)
        self._store.add("assistant", text)
        self.chat.set_input_enabled(True)
        self.pet.done()
        logger.info(f"Vision response: {text[:80]}...")

    def _on_vision_error(self, error: Exception):
        msg = f"❌ 图片分析失败：{type(error).__name__}: {error}"
        self.chat.add_system_message(msg)
        logger.exception("Vision request failed")
        self.chat.set_input_enabled(True)
        self.pet.done()

    # ── 剪贴板 ──

    def _on_clipboard_text(self, text: str):
        if self.chat.isVisible():
            preview = text[:60] + ("..." if len(text) > 60 else "")
            self.chat.add_system_message(f"📋 已复制：{preview}")
            self.pet.show_status("📋 复制了！", 2000)

    def _quit(self):
        if self._quitting:
            return
        self._quitting = True
        self.tray.hide()
        self.chat.close()
        self.pet.close()
        self.app.quit()

    def _cleanup(self):
        logger.info("Shutting down...")
        try:
            self._hotkey.stop()
        except Exception:
            pass
        try:
            self._clipboard.stop()
        except Exception:
            pass
        try:
            self._store.close()
        except Exception:
            pass
