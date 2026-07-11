"""截屏工具 — 全屏截图（非交互式，供 Agent 调用）。"""
from __future__ import annotations

import base64
from io import BytesIO
from typing import Any

from PySide6.QtWidgets import QApplication

from agent_runtime import ToolSpec, ToolHandler, ToolResult, ToolExecutionContext

SCREENSHOT_SPEC = ToolSpec(
    name="screenshot",
    description="截取当前屏幕全屏截图，返回 base64 编码的 PNG 图片。用于分析屏幕上的内容。",
    parameters_schema={
        "type": "object",
        "properties": {},
        "additionalProperties": False,
    },
    tags=frozenset({"desktop", "read_only"}),
    timeout_seconds=10.0,
)


class ScreenshotTool:
    spec: ToolSpec = SCREENSHOT_SPEC

    async def execute(
        self,
        arguments: dict[str, Any],
        context: ToolExecutionContext,
        on_update=None,
    ) -> ToolResult:
        screen = QApplication.primaryScreen()
        if screen is None:
            return ToolResult(output="无可用屏幕", status="error", error_message="No screen available")

        pixmap = screen.grabWindow(0)
        if pixmap.isNull():
            return ToolResult(output="截图失败", status="error", error_message="grabWindow returned null")

        buf = BytesIO()
        pixmap.save(buf, "PNG")
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")

        return ToolResult(
            output=f"[截图完成，尺寸: {pixmap.width()}x{pixmap.height()}，base64 长度: {len(b64)}]",
            structured_data={
                "base64": b64,
                "width": pixmap.width(),
                "height": pixmap.height(),
                "format": "png",
            },
        )
