"""剪贴板工具 — 读写系统剪贴板。"""
from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import QApplication

from agent_runtime import ToolSpec, ToolHandler, ToolResult, ToolExecutionContext

# ── clipboard_read ─────────────────────────────────────────────

CLIPBOARD_READ_SPEC = ToolSpec(
    name="clipboard_read",
    description="读取系统剪贴板的文本内容。",
    parameters_schema={
        "type": "object",
        "properties": {},
        "additionalProperties": False,
    },
    tags=frozenset({"desktop", "read_only"}),
    timeout_seconds=5.0,
)


class ClipboardReadTool:
    spec: ToolSpec = CLIPBOARD_READ_SPEC

    async def execute(
        self,
        arguments: dict[str, Any],
        context: ToolExecutionContext,
        on_update=None,
    ) -> ToolResult:
        clipboard = QApplication.clipboard()
        if clipboard is None:
            return ToolResult(output="剪贴板不可用", status="error", error_message="QClipboard unavailable")
        text = clipboard.text()
        if not text:
            return ToolResult(output="(剪贴板为空)")
        return ToolResult(output=text, structured_data={"text": text})


# ── clipboard_write ────────────────────────────────────────────

CLIPBOARD_WRITE_SPEC = ToolSpec(
    name="clipboard_write",
    description="将文本写入系统剪贴板。",
    parameters_schema={
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "要写入剪贴板的文本。"},
        },
        "required": ["text"],
        "additionalProperties": False,
    },
    tags=frozenset({"desktop", "write"}),
    timeout_seconds=5.0,
)


class ClipboardWriteTool:
    spec: ToolSpec = CLIPBOARD_WRITE_SPEC

    async def execute(
        self,
        arguments: dict[str, Any],
        context: ToolExecutionContext,
        on_update=None,
    ) -> ToolResult:
        text = arguments.get("text", "")
        clipboard = QApplication.clipboard()
        if clipboard is None:
            return ToolResult(output="剪贴板不可用", status="error", error_message="QClipboard unavailable")
        clipboard.setText(text)
        return ToolResult(output=f"已写入剪贴板（{len(text)} 字符）", structured_data={"length": len(text)})
