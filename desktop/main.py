"""AgentLabKit Desktop — 入口。"""
import fcntl
import sys
from pathlib import Path

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


def main():
    if not acquire_single_instance():
        print("AgentLabKit Desktop 已在运行中，禁止重复启动。")
        sys.exit(1)

    from app.desktop_app import DesktopApp
    desktop = DesktopApp()
    sys.exit(desktop.run())


if __name__ == "__main__":
    main()
