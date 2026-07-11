"""Bash 工具 — 执行 shell 命令。"""
from __future__ import annotations

import asyncio
from typing import Any

from agent_runtime import ToolSpec, ToolHandler, ToolResult, ToolExecutionContext

BASH_SPEC = ToolSpec(
    name="bash",
    description="在用户 home 目录下执行 shell 命令，返回 stdout 和 stderr。谨慎使用。",
    parameters_schema={
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "要执行的 shell 命令。"},
            "timeout": {"type": "integer", "description": "超时秒数，默认 30。"},
        },
        "required": ["command"],
        "additionalProperties": False,
    },
    tags=frozenset({"desktop", "shell", "write"}),
    timeout_seconds=60.0,
    is_idempotent=False,
)


class BashTool:
    spec: ToolSpec = BASH_SPEC

    async def execute(
        self,
        arguments: dict[str, Any],
        context: ToolExecutionContext,
        on_update=None,
    ) -> ToolResult:
        command = arguments.get("command", "")
        timeout = arguments.get("timeout", 30)

        if not command.strip():
            return ToolResult(output="命令不能为空", status="error", error_message="Empty command")

        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(__import__("pathlib").Path.home()),
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)

            stdout_text = stdout.decode("utf-8", errors="replace").rstrip()
            stderr_text = stderr.decode("utf-8", errors="replace").rstrip()

            parts = []
            if stdout_text:
                parts.append(stdout_text)
            if stderr_text:
                parts.append(f"[stderr]\n{stderr_text}")
            parts.append(f"[exit code: {proc.returncode}]")

            output = "\n".join(parts)
            status = "success" if proc.returncode == 0 else "error"

            return ToolResult(
                output=output,
                structured_data={"exit_code": proc.returncode, "stdout": stdout_text, "stderr": stderr_text},
                status=status,
                error_message=stderr_text if proc.returncode != 0 else None,
            )
        except asyncio.TimeoutError:
            return ToolResult(
                output=f"命令超时（{timeout}秒）",
                status="timeout",
                error_message=f"Command timed out after {timeout}s",
            )
        except Exception as e:
            return ToolResult(output=f"执行失败: {e}", status="error", error_message=str(e))
