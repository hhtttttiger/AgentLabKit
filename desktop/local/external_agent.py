"""The deliberately small Codex CLI boundary used by Desktop Local Mode.

This module owns process mechanics only. It does not turn terminal text into
synthetic Runtime spans or claim token/cost facts that the CLI did not provide.
"""
from __future__ import annotations

import asyncio
import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping

from agent_runtime.contracts.run import AgentRun, RunTarget


@dataclass(frozen=True)
class ExternalAgentAvailability:
    agent_id: str
    display_name: str
    kind: str
    availability: str
    executable: str | None = None
    version: str | None = None
    message: str | None = None


@dataclass(frozen=True)
class ExternalProcessResult:
    output: str
    stderr: str
    returncode: int
    events: tuple[Mapping[str, Any], ...] = field(default_factory=tuple)


def detect_codex(*, which: Callable[[str], str | None] = shutil.which) -> ExternalAgentAvailability:
    executable = which("codex")
    if executable is None:
        return ExternalAgentAvailability(
            agent_id="codex", display_name="Codex", kind="external",
            availability="not_installed", message="Codex CLI is not installed.",
        )
    version = None
    try:
        # This is intentionally best effort. Availability is based on the
        # executable, while version is useful provenance when it is available.
        import subprocess
        completed = subprocess.run([executable, "--version"], capture_output=True, text=True, timeout=3, check=False)
        version = (completed.stdout or completed.stderr).strip() or None
    except (OSError, subprocess.SubprocessError):
        pass
    return ExternalAgentAvailability(
        agent_id="codex", display_name="Codex", kind="external",
        availability="ready", executable=executable, version=version,
    )


def _message_from_event(event: Mapping[str, Any]) -> str | None:
    item = event.get("item")
    if not isinstance(item, Mapping):
        return None
    if item.get("type") not in {"agent_message", "assistant_message", "message"}:
        return None
    text = item.get("text") or item.get("content")
    if isinstance(text, str):
        return text
    if isinstance(text, list):
        parts = [part.get("text", "") for part in text if isinstance(part, Mapping)]
        return "".join(part for part in parts if part)
    return None


class ExternalAgentRunner:
    """Run exactly one external CLI, currently Codex, in a selected workspace."""

    def __init__(self, *, availability: ExternalAgentAvailability | None = None, executable: str | None = None, version: str | None = None) -> None:
        # Capability detection belongs to LocalComposition's catalog lifecycle,
        # never to each execution request.
        self.executable = executable or (availability.executable if availability else None)
        self.version = version or (availability.version if availability else None)

    def update_availability(self, availability: ExternalAgentAvailability) -> None:
        self.executable = availability.executable
        self.version = availability.version

    async def execute(
        self,
        *,
        input: str,
        target: RunTarget,
        working_directory: str | Path,
        metadata: Mapping[str, object] | None = None,
    ) -> AgentRun:
        if not self.executable:
            raise FileNotFoundError("Codex CLI is not installed")
        workspace = Path(working_directory).expanduser().resolve()
        if not workspace.is_dir():
            raise ValueError(f"working directory does not exist: {workspace}")
        result = await self._run_process(input, workspace)
        merged_metadata = {
            **dict(metadata or {}),
            "execution_kind": "external",
            "external_agent_id": "codex",
            "external_executable": self.executable,
            "working_directory": str(workspace),
            "external_returncode": result.returncode,
            "external_events": list(result.events),
        }
        if self.version:
            merged_metadata["external_version"] = self.version
        run = AgentRun(
            input=input,
            target=RunTarget(type="agent", kind="external", agent_key=target.agent_key or "codex", agent_version=self.version),
            session_id="external-codex",
            metadata=merged_metadata,
        )
        output = result.output.strip()
        if result.returncode == 0:
            run.mark_completed(output=output)
        else:
            run.mark_failed(
                error_code="external_process_failed",
                error_message=(result.stderr.strip() or output or f"Codex exited with {result.returncode}"),
            )
            if output:
                run.output = output
        return run

    async def _run_process(self, prompt: str, workspace: Path) -> ExternalProcessResult:
        process = await asyncio.create_subprocess_exec(
            self.executable, "exec", "--json", "--ephemeral", "--skip-git-repo-check",
            "--cd", str(workspace), prompt,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await process.communicate()
        except asyncio.CancelledError:
            # A cancelled Desktop request owns this child process. Terminate
            # it explicitly so an external CLI cannot outlive the request.
            process.terminate()
            await process.wait()
            raise
        raw = stdout.decode("utf-8", errors="replace")
        events: list[Mapping[str, Any]] = []
        messages: list[str] = []
        for line in raw.splitlines():
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(event, Mapping):
                events.append(event)
                message = _message_from_event(event)
                if message:
                    messages.append(message)
        return ExternalProcessResult(
            output="\n".join(messages) or raw,
            stderr=stderr.decode("utf-8", errors="replace"),
            returncode=await process.wait(),
            events=tuple(events),
        )


__all__ = ["ExternalAgentAvailability", "ExternalAgentRunner", "ExternalProcessResult", "detect_codex"]
