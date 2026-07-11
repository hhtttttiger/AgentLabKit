"""桌面端工具注册表 — 组装所有桌面工具。"""
from __future__ import annotations

from agent_runtime import ToolRegistry

from tools.clipboard import CLIPBOARD_READ_SPEC, ClipboardReadTool, CLIPBOARD_WRITE_SPEC, ClipboardWriteTool
from tools.screen import SCREENSHOT_SPEC, ScreenshotTool
from tools.filesystem import (
    READ_FILE_SPEC, ReadFileTool,
    LIST_DIR_SPEC, ListDirTool,
    SEARCH_FILES_SPEC, SearchFilesTool,
)
from tools.bash import BASH_SPEC, BashTool


def create_desktop_tool_registry(enable_bash: bool = False) -> ToolRegistry:
    """创建桌面端工具注册表。

    Args:
        enable_bash: 是否启用 bash 工具（默认不启用，需显式开启）。
    """
    registry = ToolRegistry()  # 自带 knowledge_search

    # 剪贴板
    registry.register(CLIPBOARD_READ_SPEC, ClipboardReadTool())
    registry.register(CLIPBOARD_WRITE_SPEC, ClipboardWriteTool())

    # 截屏
    registry.register(SCREENSHOT_SPEC, ScreenshotTool())

    # 文件系统
    registry.register(READ_FILE_SPEC, ReadFileTool())
    registry.register(LIST_DIR_SPEC, ListDirTool())
    registry.register(SEARCH_FILES_SPEC, SearchFilesTool())

    # Shell（可选）
    if enable_bash:
        registry.register(BASH_SPEC, BashTool())

    return registry
