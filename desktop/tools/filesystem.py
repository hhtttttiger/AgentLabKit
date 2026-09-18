"""文件系统工具 — 读文件、列目录、搜索文件内容。

Desktop Local Mode 将 selected workspace 作为一次执行的文件系统边界。
这会减少意外的路径逃逸，但不是 OS security sandbox。
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from agent_runtime import ToolSpec, ToolHandler, ToolResult, ToolExecutionContext

# ── 辅助 ───────────────────────────────────────────────────────

def canonicalize_workspace(working_directory: str | None) -> Path:
    """Resolve the selected workspace once before tools consume it."""
    if not working_directory:
        raise ValueError("未选择 workspace，无法执行文件操作")
    workspace = Path(working_directory).expanduser().resolve()
    if not workspace.exists() or not workspace.is_dir():
        raise ValueError(f"workspace 不存在或不是目录: {workspace}")
    return workspace


def resolve_workspace_path(path_str: str, workspace_root: Path | str) -> Path:
    """Resolve a requested path and reject symlink/path escapes."""
    root = Path(workspace_root).expanduser().resolve()
    raw = Path(path_str).expanduser()
    candidate = raw if raw.is_absolute() else root / raw
    resolved = candidate.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as error:
        raise ValueError(f"路径 {resolved} 超出 workspace 范围（workspace: {root}）") from error
    return resolved


def _safe_path(path_str: str, working_directory: str | None = None) -> Path:
    """Resolve a path inside the canonical workspace, including symlink checks."""
    return resolve_workspace_path(path_str, canonicalize_workspace(working_directory))


# ── read_file ──────────────────────────────────────────────────

READ_FILE_SPEC = ToolSpec(
    name="read_file",
    description="读取 workspace 内文件的文本内容。",
    parameters_schema={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "文件路径。"},
            "max_lines": {"type": "integer", "description": "最大读取行数，默认 200。"},
        },
        "required": ["path"],
        "additionalProperties": False,
    },
    tags=frozenset({"desktop", "filesystem", "read_only"}),
    timeout_seconds=10.0,
)


class ReadFileTool:
    spec: ToolSpec = READ_FILE_SPEC

    async def execute(
        self,
        arguments: dict[str, Any],
        context: ToolExecutionContext,
        on_update=None,
    ) -> ToolResult:
        try:
            p = _safe_path(arguments["path"], context.metadata.get("working_directory"))
        except ValueError as e:
            return ToolResult(output=str(e), status="error", error_message=str(e))

        if not p.exists():
            return ToolResult(output=f"文件不存在: {p}", status="error", error_message="File not found")
        if not p.is_file():
            return ToolResult(output=f"不是文件: {p}", status="error", error_message="Not a file")

        max_lines = arguments.get("max_lines", 200)
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
            lines = text.splitlines(keepends=True)
            truncated = len(lines) > max_lines
            content = "".join(lines[:max_lines])
            header = f"文件: {p} ({len(lines)} 行)"
            if truncated:
                header += f" [截断至前 {max_lines} 行]"
            return ToolResult(output=f"{header}\n{content}")
        except Exception as e:
            return ToolResult(output=f"读取失败: {e}", status="error", error_message=str(e))


# ── list_dir ───────────────────────────────────────────────────

LIST_DIR_SPEC = ToolSpec(
    name="list_dir",
    description="列出 workspace 内目录下的文件和子目录。",
    parameters_schema={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "目录路径。"},
        },
        "required": ["path"],
        "additionalProperties": False,
    },
    tags=frozenset({"desktop", "filesystem", "read_only"}),
    timeout_seconds=10.0,
)


class ListDirTool:
    spec: ToolSpec = LIST_DIR_SPEC

    async def execute(
        self,
        arguments: dict[str, Any],
        context: ToolExecutionContext,
        on_update=None,
    ) -> ToolResult:
        try:
            p = _safe_path(arguments["path"], context.metadata.get("working_directory"))
        except ValueError as e:
            return ToolResult(output=str(e), status="error", error_message=str(e))

        if not p.exists():
            return ToolResult(output=f"路径不存在: {p}", status="error", error_message="Path not found")
        if not p.is_dir():
            return ToolResult(output=f"不是目录: {p}", status="error", error_message="Not a directory")

        try:
            entries = sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
            lines = []
            for entry in entries[:200]:  # 限制 200 条
                kind = "📁" if entry.is_dir() else "📄"
                size = entry.stat().st_size if entry.is_file() else 0
                lines.append(f"{kind} {entry.name}  ({size} B)" if size else f"{kind} {entry.name}")
            header = f"目录: {p} ({len(entries)} 项)"
            if len(entries) > 200:
                header += " [截断至 200 项]"
            return ToolResult(output=f"{header}\n" + "\n".join(lines))
        except PermissionError:
            return ToolResult(output=f"无权限访问: {p}", status="error", error_message="Permission denied")


# ── search_files ───────────────────────────────────────────────

SEARCH_FILES_SPEC = ToolSpec(
    name="search_files",
    description="在 workspace 内搜索包含指定文本的文件（类似 grep）。",
    parameters_schema={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "搜索目录。"},
            "pattern": {"type": "string", "description": "要搜索的文本（区分大小写）。"},
            "max_results": {"type": "integer", "description": "最大结果数，默认 50。"},
        },
        "required": ["path", "pattern"],
        "additionalProperties": False,
    },
    tags=frozenset({"desktop", "filesystem", "read_only"}),
    timeout_seconds=30.0,
)


class SearchFilesTool:
    spec: ToolSpec = SEARCH_FILES_SPEC

    async def execute(
        self,
        arguments: dict[str, Any],
        context: ToolExecutionContext,
        on_update=None,
    ) -> ToolResult:
        try:
            p = _safe_path(arguments["path"], context.metadata.get("working_directory"))
        except ValueError as e:
            return ToolResult(output=str(e), status="error", error_message=str(e))

        pattern = arguments.get("pattern", "")
        max_results = arguments.get("max_results", 50)

        if not pattern:
            return ToolResult(output="搜索模式不能为空", status="error", error_message="Empty pattern")

        results = []
        try:
            for root, dirs, files in os.walk(p):
                # 跳过隐藏目录和常见大目录
                dirs[:] = [d for d in dirs if not d.startswith(".") and d not in {"node_modules", "__pycache__", ".git", "venv"}]
                for fname in files:
                    fpath = Path(root) / fname
                    try:
                        fpath = resolve_workspace_path(str(fpath), p)
                    except ValueError:
                        continue
                    if fpath.stat().st_size > 1_000_000:  # 跳过 >1MB 文件
                        continue
                    try:
                        text = fpath.read_text(encoding="utf-8", errors="ignore")
                        for i, line in enumerate(text.splitlines(), 1):
                            if pattern in line:
                                results.append(f"{fpath}:{i}: {line.rstrip()[:200]}")
                                if len(results) >= max_results:
                                    break
                    except (PermissionError, OSError):
                        continue
                    if len(results) >= max_results:
                        break
                if len(results) >= max_results:
                    break
        except Exception as e:
            return ToolResult(output=f"搜索失败: {e}", status="error", error_message=str(e))

        if not results:
            return ToolResult(output=f"在 {p} 中未找到 '{pattern}'")
        header = f"在 {p} 中搜索 '{pattern}'，找到 {len(results)} 条结果"
        if len(results) >= max_results:
            header += f"（截断至 {max_results}）"
        return ToolResult(output=f"{header}\n" + "\n".join(results))
