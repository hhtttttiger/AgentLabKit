"""AgentLabKit Desktop — 主入口。

整合桌宠、托盘、对话面板、LLM Gateway、聊天历史持久化。
"""
import fcntl
import logging
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

# ── 单实例检查 ──
LOCK_FILE = Path.home() / ".config" / "agentlabkit" / "desktop.lock"
LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
_lock_fd = None

def acquire_single_instance() -> bool:
    global _lock_fd
    try:
        _lock_fd = open(LOCK_FILE, "w")
        fcntl.flock(_lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        _lock_fd.write(str(__import__("os").getpid()))
        _lock_fd.flush()
        return True
    except OSError:
        return False

from config import AppConfig, CONFIG_FILE
from pet import PetWindow
from tray import TrayManager
from chat import ChatPanel
from chat_store import ChatStore
from bootstrap import create_gateway
from async_bridge import run_async
from llm_gateway import TextGenerateRequest

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
        self._quitting = False  # 防止重复退出

        # ── 配置 ──
        self.config = AppConfig.load()
        logger.info(f"Config: provider={self.config.llm.provider}, model={self.config.llm.model}")
        self._gateway = None

        # ── 聊天存储 ──
        self._store = ChatStore()

        # ── 对话面板 ──
        self.chat = ChatPanel()
        self.chat.message_sent.connect(self._on_message_sent)

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
        self.tray.quit_requested.connect(self._quit)
        self.tray.show()

        # ── Gateway ──
        self._init_gateway()

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

    def _init_gateway(self):
        llm = self.config.llm
        if not llm.api_key:
            self.chat.add_system_message(f"⚠️ 未配置 API Key，请编辑：\n{CONFIG_FILE}")
            return
        try:
            self._gateway = create_gateway(llm)
            self.chat.add_system_message(f"已连接 {llm.provider}（{llm.model}）")
            logger.info("Gateway initialized")
        except Exception as e:
            self.chat.add_system_message(f"⚠️ 连接失败：{e}")
            logger.exception("Gateway init failed")

    def run(self) -> int:
        return self.app.exec()

    def _toggle_chat(self):
        if self.chat.isVisible():
            self.chat.hide()
        else:
            self.chat.show()
            self.chat.activateWindow()
            self.chat.raise_()

    def _on_message_sent(self, text: str):
        if not self._gateway:
            self.chat.add_system_message("⚠️ LLM 未连接，请检查配置")
            return

        self._store.add("user", text)
        self.chat.set_input_enabled(False)
        logger.info(f"Sending: {text[:80]}...")

        request = TextGenerateRequest(
            model=self.config.llm.model,
            prompt=text,
            temperature=0.7,
            max_output_tokens=1024,
        )
        run_async(
            self._gateway.generate_text(request),
            on_result=self._on_llm_response,
            on_error=self._on_llm_error,
            parent=self.chat,
        )

    def _on_llm_response(self, response):
        if response.error:
            msg = f"❌ {response.error.code}: {response.error.message}"
            self.chat.add_system_message(msg)
            logger.error(f"LLM error: {response.error}")
        else:
            self._store.add("assistant", response.text)
            self.chat.add_message(response.text, is_user=False)
            logger.info(f"Response: {response.text[:80]}...")
        self.chat.set_input_enabled(True)

    def _on_llm_error(self, error: Exception):
        msg = f"❌ 请求失败：{type(error).__name__}: {error}"
        self.chat.add_system_message(msg)
        logger.exception("LLM request failed")
        self.chat.set_input_enabled(True)

    def _quit(self):
        """主动退出：关闭窗口，触发 aboutToQuit。"""
        if self._quitting:
            return
        self._quitting = True
        self.tray.hide()
        self.chat.close()
        self.pet.close()
        self.app.quit()

    def _cleanup(self):
        """aboutToQuit 回调：释放资源。"""
        logger.info("Shutting down...")
        try:
            self._store.close()
        except Exception:
            pass


def main():
    if not acquire_single_instance():
        print("AgentLabKit Desktop 已在运行中，禁止重复启动。")
        sys.exit(1)

    desktop = DesktopApp()
    sys.exit(desktop.run())


if __name__ == "__main__":
    main()
