"""Agent turn streaming — bridges ``agent_runtime.stream_turn`` to the frontend SSE contract.

The runtime emits :class:`AgentTurnStreamEvent` (snake_case fields, event types
``turn_context`` / ``reply_delta`` / ``reply_completed`` / …, no ``runId``).
The frontend expects :class:`AgentStreamEvent` (camelCase fields, types
``context`` / ``reply_delta`` / ``completed`` / …, ``runId`` on every event —
see ``frontend/.../ai-chat/lib/contracts.ts``). This module owns that mapping,
drives the stream, surfaces runtime errors as ``error`` events (the runtime
*raises* ``AgentError`` rather than yielding it), and persists one
``AgentExecutionAudit`` row per turn.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Any, AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from agent_runtime import AgentMessage, AgentRuntime, AgentTurnRequest, ToolExecutionRecord
from agent_runtime.errors import AgentError

from modules.agent.models import AgentExecutionAudit

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────
# Runtime event → frontend SSE payload
# ──────────────────────────────────────────────────────────────────────────


def map_stream_event(
    event: Any,
    *,
    run_id: str,
    agent_key: str,
    agent_version: int | None,
) -> dict[str, Any]:
    """Map a single ``AgentTurnStreamEvent`` to a frontend SSE dict.

    Injects ``runId`` / ``sessionId`` / ``traceId`` / ``agentKey`` /
    ``agentVersion`` on every event (the runtime events carry none of these
    except session/trace ids), and renames the two event types that differ:
    ``turn_context`` → ``context`` and ``reply_completed`` → ``completed``.
    """
    base: dict[str, Any] = {
        "runId": run_id,
        "sessionId": event.session_id,
        "traceId": event.trace_id,
        "agentKey": agent_key or event.agent_key,
        "agentVersion": agent_version if agent_version is not None else event.agent_version,
    }

    event_type = event.event_type
    if event_type == "turn_context":
        return {**base, "type": "context", "appliedSkills": _applied_skills(event.applied_skills)}
    if event_type == "reply_delta":
        return {**base, "type": "reply_delta", "delta": event.delta or ""}
    if event_type == "reply_completed":
        return {
            **base,
            "type": "completed",
            "replyText": event.reply_text,
            "usage": _usage(event.usage),
            "action": "reply",
            "status": "succeeded",
        }
    if event_type == "tool_call":
        return {
            **base,
            "type": "tool_call",
            "toolName": event.tool_name,
            "toolArguments": event.tool_arguments,
            "toolEvent": _tool_event(event.tool_event),
        }
    if event_type == "tool_result":
        return {**base, "type": "tool_result", "toolEvent": _tool_event(event.tool_event)}
    if event_type == "delegation_delta":
        return {
            **base,
            "type": "delegation_delta",
            "delta": event.delta,
            "delegationAgentKey": event.delegation_agent_key,
        }
    if event_type == "handoff":
        return {
            **base,
            "type": "handoff",
            "replyText": event.reply_text,
            "handoffReason": event.handoff_reason,
            "usage": _usage(event.usage),
            "action": "handoff",
            "status": "succeeded",
        }
    # Unknown event type — pass through minimally so the stream never drops it.
    return {**base, "type": event_type, "replyText": event.reply_text}


def _tool_event(record: ToolExecutionRecord | None) -> dict[str, Any] | None:
    if record is None:
        return None
    return {
        "toolName": record.tool_name,
        "status": record.status,
        "arguments": record.arguments,
        "outputText": record.output_text,
        "errorMessage": record.error_message,
        "displayName": record.display_name,
        "sourceType": record.source_type,
        "sourceRef": record.source_ref,
        "tags": list(record.tags),
        "durationMs": record.duration_ms,
    }


def _usage(usage: Any) -> dict[str, Any] | None:
    if usage is None:
        return None
    return {
        "inputTokens": usage.input_tokens,
        "outputTokens": usage.output_tokens,
        "totalTokens": usage.total_tokens,
        "audioDurationMs": usage.audio_duration_ms,
    }


def _applied_skills(skills: Any) -> list[dict[str, Any]]:
    return [
        {
            "skillKey": skill.skill_key,
            "displayName": skill.display_name,
            "order": skill.order,
            "config": skill.config,
        }
        for skill in (skills or [])
    ]


def error_payload(
    *,
    run_id: str,
    session_id: str,
    trace_id: str,
    agent_key: str,
    agent_version: int | None,
    code: str,
    message: str,
) -> dict[str, Any]:
    return {
        "type": "error",
        "runId": run_id,
        "sessionId": session_id,
        "traceId": trace_id,
        "agentKey": agent_key,
        "agentVersion": agent_version,
        "status": "failed",
        "errorCode": code,
        "errorMessage": message,
    }


# ──────────────────────────────────────────────────────────────────────────
# Stream driver
# ──────────────────────────────────────────────────────────────────────────


async def run_agent_turn_stream(
    runtime: AgentRuntime,
    *,
    agent_key: str,
    agent_version: int,
    message: str,
    session_id: str | None,
    history: list[AgentMessage],
    session_factory: async_sessionmaker[AsyncSession],
    user_id: str | None = None,
) -> AsyncIterator[str]:
    """Run one agent turn and yield SSE ``data:`` lines.

    Always terminates with ``data: [DONE]``. Runtime errors are converted to an
    ``error`` event so the frontend's ``onError``/terminal handling still fires
    cleanly. One ``AgentExecutionAudit`` row is written in ``finally``.
    """
    run_id = str(uuid.uuid4())
    trace_id = str(uuid.uuid4())
    effective_session_id = session_id or run_id

    request = AgentTurnRequest(
        session_id=effective_session_id,
        user_message=message,
        history=list(history),
        user_id=user_id,
        agent_key=agent_key,
        agent_version=agent_version,
        trace_id=trace_id,
    )

    started_at = time.perf_counter()
    reply_text = ""
    tool_events: list[ToolExecutionRecord] = []
    usage: Any = None
    status = "success"
    error_message: str | None = None

    def sse(payload: dict[str, Any]) -> str:
        return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    try:
        async for event in runtime.stream_turn(request):
            # Aggregate for the audit row.
            if event.event_type == "reply_delta":
                reply_text += event.delta or ""
            elif event.event_type in ("reply_completed", "handoff") and event.reply_text:
                reply_text = event.reply_text
            if event.event_type in ("tool_call", "tool_result") and event.tool_event is not None:
                tool_events.append(event.tool_event)
            if event.usage is not None:
                usage = event.usage

            yield sse(
                map_stream_event(
                    event, run_id=run_id, agent_key=agent_key, agent_version=agent_version
                )
            )
    except AgentError as exc:
        status = "error"
        error_message = exc.message
        yield sse(
            error_payload(
                run_id=run_id, session_id=effective_session_id, trace_id=trace_id,
                agent_key=agent_key, agent_version=agent_version,
                code=exc.code.value if exc.code is not None else "runtime_error",
                message=exc.message,
            )
        )
    except Exception as exc:  # noqa: BLE001 — never let the SSE stream die silently
        logger.exception("agent_turn_stream failed agent_key=%s run_id=%s", agent_key, run_id)
        status = "error"
        error_message = str(exc)
        yield sse(
            error_payload(
                run_id=run_id, session_id=effective_session_id, trace_id=trace_id,
                agent_key=agent_key, agent_version=agent_version,
                code="runtime_error", message=str(exc),
            )
        )
    finally:
        yield "data: [DONE]\n\n"
        duration_ms = int((time.perf_counter() - started_at) * 1000)
        await write_audit(
            session_factory,
            agent_key=agent_key,
            run_id=run_id,
            agent_version=agent_version,
            message=message,
            reply_text=reply_text,
            tool_events=tool_events,
            usage=usage,
            status=status,
            duration_ms=duration_ms,
            error_message=error_message,
        )


async def write_audit(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    agent_key: str,
    run_id: str,
    agent_version: int,
    message: str,
    reply_text: str,
    tool_events: list[ToolExecutionRecord],
    usage: Any,
    status: str,
    duration_ms: int,
    error_message: str | None,
) -> None:
    """Persist one execution audit row. Best-effort — never blocks the response."""
    try:
        async with session_factory() as session:
            session.add(
                AgentExecutionAudit(
                    agent_key=agent_key,
                    run_id=run_id,
                    agent_version=agent_version,
                    input_summary=(message or "")[:500],
                    output_summary=(reply_text or "")[:500],
                    tool_calls_json=[te.model_dump() for te in tool_events],
                    status=status,
                    duration_ms=duration_ms,
                    token_usage_json=usage.model_dump() if usage is not None else {},
                    error_message=error_message,
                )
            )
            await session.commit()
    except Exception:
        logger.exception("agent_turn audit write failed run_id=%s agent_key=%s", run_id, agent_key)
