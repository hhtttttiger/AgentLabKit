from __future__ import annotations

import asyncio
import base64
import contextlib
import json
import logging
from datetime import datetime, timezone
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from ...config import ProviderConfig
from ...core.adapters import RealtimeAdapter
from ...errors import GatewayError, GatewayErrorCode
from ...models import ProviderId, RealtimeClientEvent, RealtimeServerEvent, UsageInfo
from ...provider_runtime import RuntimeProviderConfig
from ...usage_info import usage_from_openai_usage_payload
from ..shared.common import resolve_provider_secrets
from ..shared.openai_transport import (
    build_openai_realtime_headers,
    build_openai_realtime_url,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RealtimeSessionCapabilities:
    supported_turn_detection_modes: frozenset[str]
    supported_noise_reduction_modes: frozenset[str]
    turn_detection_mode_map: dict[str, str] | None = None
    noise_reduction_mode_map: dict[str, str] | None = None


_DEFAULT_REALTIME_SESSION_CAPABILITIES = RealtimeSessionCapabilities(
    supported_turn_detection_modes=frozenset(),
    supported_noise_reduction_modes=frozenset(),
    turn_detection_mode_map=None,
    noise_reduction_mode_map=None,
)


def _load_websockets_connect():
    try:
        from websockets.asyncio.client import connect  # type: ignore
    except ImportError:
        try:
            from websockets.client import connect  # type: ignore
        except ImportError as exc:  # pragma: no cover - runtime dependency
            raise RuntimeError(
                "websockets is not installed. Install project dependencies first."
            ) from exc
    return connect

def _resolve_session_type(metadata: dict[str, Any]) -> str:
    configured = (metadata.get("session_type") or "").strip().lower()
    if configured in {"realtime", "transcription"}:
        return configured
    return "realtime"


def _parse_audio_format(mime_type: str | None) -> str | None:
    if not mime_type:
        return None
    normalized = mime_type.strip().lower()
    if not normalized:
        return None
    if normalized == "audio/pcm":
        return "pcm16"
    return normalized


def _parse_audio_rate(metadata: dict[str, Any], key: str, default: int | None = None) -> int | None:
    raw = (metadata.get(key) or "").strip()
    if not raw:
        return default
    try:
        parsed = int(raw)
    except ValueError:
        return default
    return parsed if parsed > 0 else default


def _apply_session_output_preference(
    session: dict[str, Any],
    *,
    metadata: dict[str, Any],
) -> None:
    is_transcription_only = metadata.get("transcription_only") in {
        "1",
        "true",
        "yes",
        "on",
    }
    output_audio_enabled = metadata.get("output_audio") in {"1", "true", "yes", "on"}

    if output_audio_enabled:
        session["modalities"] = ["text", "audio"]
    elif is_transcription_only:
        session["modalities"] = ["text"]


def _resolve_turn_detection_mode(metadata: dict[str, Any]) -> str | None:
    configured = (metadata.get("turn_detection_mode") or "").strip().lower()
    return configured or None


def _resolve_realtime_session_capabilities(provider: ProviderId) -> RealtimeSessionCapabilities:
    return _DEFAULT_REALTIME_SESSION_CAPABILITIES


def _apply_turn_detection_preferences(
    session: dict[str, Any],
    *,
    metadata: dict[str, Any],
    capabilities: RealtimeSessionCapabilities,
) -> None:
    mode = _resolve_turn_detection_mode(metadata)
    if not mode:
        return

    if mode in {"manual", "none", "disabled", "off"}:
        session["turn_detection"] = None
        return

    if mode not in capabilities.supported_turn_detection_modes:
        return

    provider_turn_detection_mode = (capabilities.turn_detection_mode_map or {}).get(
        mode,
        mode,
    )

    turn_detection = {
        "type": provider_turn_detection_mode,
        "threshold": _parse_int(metadata.get("turn_detection_threshold"), 300),
        "prefix_padding_ms": _parse_int(metadata.get("turn_detection_prefix_padding_ms"), 300),
        "silence_duration_ms": _parse_int(metadata.get("silence_duration_ms"), 420),
    }

    session["turn_detection"] = turn_detection


def _parse_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _apply_input_audio_preprocessing(
    session: dict[str, Any],
    *,
    metadata: dict[str, Any],
    capabilities: RealtimeSessionCapabilities,
) -> None:
    noise_reduction_mode = (metadata.get("noise_reduction_mode") or "").strip().lower()
    if noise_reduction_mode in capabilities.supported_noise_reduction_modes:
        provider_noise_reduction_mode = (
            capabilities.noise_reduction_mode_map or {}
        ).get(noise_reduction_mode, noise_reduction_mode)
        session["input_audio_preprocessing"] = {"noise_reduction": {"type": provider_noise_reduction_mode}}


def map_client_event_to_openai(event: RealtimeClientEvent) -> list[dict[str, Any]]:
    if event.event_type == "session_start":
        session: dict[str, Any] = {"type": _resolve_session_type(event.metadata)}
        capabilities = _resolve_realtime_session_capabilities(event.provider)

        if event.metadata.get("instructions"):
            session["instructions"] = event.metadata["instructions"]
        if event.tools:
            session["tools"] = [dict(tool) for tool in event.tools]
            if event.tool_choice:
                session["tool_choice"] = event.tool_choice

        if event.metadata.get("input_audio_transcription_model"):
            session["input_audio_transcription"] = {
                "model": event.metadata["input_audio_transcription_model"]
            }

        if event.metadata.get("voice"):
            session["voice"] = event.metadata["voice"]

        if input_format := _parse_audio_format(event.metadata.get("input_audio_format")):
            session["input_audio_format"] = input_format
        if output_format := _parse_audio_format(event.metadata.get("output_audio_format")):
            session["output_audio_format"] = output_format

        _apply_session_output_preference(
            session,
            metadata=event.metadata,
        )
        _apply_turn_detection_preferences(
            session,
            metadata=event.metadata,
            capabilities=capabilities,
        )

        return [{"type": "session.update", "session": session}]
    if event.event_type == "text":
        response: dict[str, Any] = {}
        if event.metadata.get("instructions"):
            response["instructions"] = event.metadata["instructions"]
        return [
            {
                "type": "conversation.item.create",
                "item": {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": event.text or ""}],
                },
            },
            {"type": "response.create", "response": response} if response else {"type": "response.create"},
        ]
    if event.event_type == "audio_chunk":
        if event.audio_chunk is None:
            return []
        return [
            {
                "type": "input_audio_buffer.append",
                "audio": base64.b64encode(event.audio_chunk).decode("ascii"),
            }
        ]
    if event.event_type == "audio_commit":
        events = [{"type": "input_audio_buffer.commit"}]
        should_generate_transcript_response = event.metadata.get("realtime_generated_transcript") in {
            "1",
            "true",
            "yes",
            "on",
        }
        if should_generate_transcript_response:
            response: dict[str, Any] = {}
            if event.metadata.get("instructions"):
                response["instructions"] = event.metadata["instructions"]
            if event.metadata.get("output_audio") in {"0", "false", "no", "off"}:
                response["modalities"] = ["text"]
            events.append(
                {"type": "response.create", "response": response}
                if response
                else {"type": "response.create"}
            )
        elif event.metadata.get("transcription_only") not in {"1", "true", "yes", "on"}:
            events.append({"type": "response.create"})
        return events
    if event.event_type == "tool_result":
        if not event.tool_call_id:
            raise GatewayError(
                GatewayErrorCode.VALIDATION_ERROR,
                "Realtime tool_result requires tool_call_id.",
                provider=event.provider,
                model=event.model,
            )
        response: dict[str, Any] = {}
        if event.metadata.get("instructions"):
            response["instructions"] = event.metadata["instructions"]
        return [
            {
                "type": "conversation.item.create",
                "item": {
                    "type": "function_call_output",
                    "call_id": event.tool_call_id,
                    "output": event.tool_output or event.text or "",
                },
            },
            {"type": "response.create", "response": response}
            if response
            else {"type": "response.create"},
        ]
    if event.event_type in {"interrupt", "cancel"}:
        return [{"type": "response.cancel"}]
    if event.event_type == "session_update":
        session = dict(event.metadata)
        session_type = session.pop("session_type", None)
        if session_type:
            session["type"] = session_type
        return [{"type": "session.update", "session": session}]
    if event.event_type == "close":
        return []
    raise GatewayError(
        GatewayErrorCode.VALIDATION_ERROR,
        f"Unsupported realtime client event '{event.event_type}'.",
        provider=event.provider,
        model=event.model,
    )


def map_openai_event_to_server(
    event: dict[str, Any], provider: ProviderId, model: str
) -> RealtimeServerEvent | None:
    event_type = event.get("type")
    if event_type in {"session.created", "session.updated"}:
        return RealtimeServerEvent(
            event_type="session_started",
            provider=provider,
            model=model,
        )
    if event_type == "input_audio_buffer.speech_started":
        return RealtimeServerEvent(
            event_type="state_changed",
            provider=provider,
            model=model,
            state="provider_speech_started",
            detail=None,
        )
    if event_type == "input_audio_buffer.speech_stopped":
        return RealtimeServerEvent(
            event_type="state_changed",
            provider=provider,
            model=model,
            state="provider_speech_stopped",
            detail=None,
        )
    if event_type in {
        "response.text.delta",
        "response.output_text.delta",
        "response.output_audio_transcript.delta",
    }:
        return RealtimeServerEvent(
            event_type="partial_text",
            provider=provider,
            model=model,
            text=event.get("delta"),
            is_final=False,
        )
    if event_type in {
        "response.text.done",
        "response.output_text.done",
        "response.output_audio_transcript.done",
    }:
        return RealtimeServerEvent(
            event_type="final_text",
            provider=provider,
            model=model,
            text=event.get("text") or event.get("transcript"),
            is_final=True,
        )
    if event_type in {"response.audio.delta", "response.output_audio.delta"}:
        payload = event.get("delta") or ""
        chunk = b""
        if payload:
            try:
                chunk = base64.b64decode(payload)
            except Exception as exc:
                raise GatewayError(
                    GatewayErrorCode.UPSTREAM_ERROR,
                    "Realtime provider returned invalid audio payload.",
                    provider=provider,
                    model=model,
                ) from exc
        return RealtimeServerEvent(
            event_type="audio_chunk",
            provider=provider,
            model=model,
            audio_chunk=chunk,
            mime_type=event.get("mime_type") or "audio/pcm",
            sequence=int(event.get("sequence_number") or event.get("sequence") or 0),
            is_final=False,
        )
    if event_type in {"response.audio.done", "response.output_audio.done"}:
        return RealtimeServerEvent(
            event_type="audio_completed",
            provider=provider,
            model=model,
            mime_type=event.get("mime_type") or "audio/pcm",
            sequence=int(event.get("sequence_number") or event.get("sequence") or 0),
            is_final=True,
        )
    if event_type == "response.output_item.done":
        item = event.get("item") or {}
        if item.get("type") == "function_call":
            return _map_function_call_event(item, provider=provider, model=model)
    if event_type == "response.function_call_arguments.done":
        if not (event.get("name") or event.get("tool_name")):
            return None
        return _map_function_call_event(event, provider=provider, model=model)
    if event_type in {
        "conversation.item.input_audio_transcription.delta",
        "conversation.item.audio_transcription.delta",
    }:
        return RealtimeServerEvent(
            event_type="partial_transcript",
            provider=provider,
            model=model,
            transcript=event.get("delta"),
            is_final=False,
        )
    if event_type in {
        "conversation.item.input_audio_transcription.completed",
        "conversation.item.audio_transcription.completed",
    }:
        return RealtimeServerEvent(
            event_type="final_transcript",
            provider=provider,
            model=model,
            transcript=event.get("transcript"),
            is_final=True,
        )
    if event_type == "response.done":
        response = event.get("response", {})
        usage = _usage_from_openai_response(response)
        if response.get("status") == "cancelled":
            return RealtimeServerEvent(
                event_type="cancelled",
                provider=provider,
                model=model,
                usage=usage,
                is_final=True,
            )
        if usage is not None:
            return RealtimeServerEvent(
                event_type="response_completed",
                provider=provider,
                model=model,
                usage=usage,
                is_final=True,
            )
    if event_type == "error":
        error = event.get("error", {})
        message = error.get("message") or "Upstream realtime error."
        raise GatewayError(
            GatewayErrorCode.UPSTREAM_ERROR,
            message,
            provider=provider,
            model=model,
        )
    return None


def _usage_from_openai_response(response: dict[str, Any]) -> UsageInfo | None:
    return usage_from_openai_usage_payload(response.get("usage"))


def _map_function_call_event(
    payload: dict[str, Any],
    *,
    provider: ProviderId,
    model: str,
) -> RealtimeServerEvent:
    return RealtimeServerEvent(
        event_type="tool_call",
        provider=provider,
        model=model,
        tool_name=payload.get("name") or payload.get("tool_name"),
        tool_call_id=payload.get("call_id") or payload.get("id"),
        tool_arguments=_parse_function_call_arguments(payload.get("arguments")),
    )


def _parse_function_call_arguments(arguments: Any) -> dict[str, Any]:
    if isinstance(arguments, dict):
        return dict(arguments)
    if isinstance(arguments, str) and arguments.strip():
        try:
            parsed = json.loads(arguments)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def event_requires_server_drain(event_type: str) -> bool:
    return event_type in {
        "session_start",
        "text",
        "audio_commit",
        "tool_result",
        "session_update",
    }


@dataclass(slots=True)
class RealtimeConnectionConfig:
    provider: ProviderId
    model: str
    url: str
    headers: dict[str, str]


@dataclass(slots=True)
class RealtimeSessionPolicy:
    response_timeout_ms: int = 30_000
    idle_timeout_ms: int = 120_000
    close_timeout_ms: int = 1_000
    stale_interrupt_drain_ms: int = 10
    ping_interval_s: float | None = 20.0
    ping_timeout_s: float | None = 60.0


@dataclass(slots=True)
class RealtimeSessionState:
    awaiting_response: bool = False
    audio_buffer_open: bool = False
    closed_by_client: bool = False
    session_started_emitted: bool = False
    backlog_ms: int = 0
    backlog_budget_ms: int = 0
    backlog_breach_reported: bool = False
    pending_event_type: str | None = None
    suppress_output_until_terminal: bool = False
    input_audio_bytes_per_ms: float | None = None
    pending_audio_completed: RealtimeServerEvent | None = None
    pending_response_metadata: dict[str, str] | None = None
    stale_interrupt_tail_pending: bool = False


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_positive_int(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _configure_session_state(state: RealtimeSessionState, event: RealtimeClientEvent) -> None:
    metadata = event.metadata or {}
    state.backlog_ms = 0
    state.backlog_budget_ms = _parse_positive_int(metadata.get("backlog_budget_ms")) or 0
    state.backlog_breach_reported = False
    if (metadata.get("input_audio_format") or "").strip().lower() != "audio/pcm":
        state.input_audio_bytes_per_ms = None
        return

    sample_rate = _parse_positive_int(metadata.get("input_audio_sample_rate_hz")) or 0
    channels = _parse_positive_int(metadata.get("input_audio_channels")) or 1
    bytes_per_sample = 2
    bytes_per_second = sample_rate * channels * bytes_per_sample
    state.input_audio_bytes_per_ms = (bytes_per_second / 1000) if bytes_per_second > 0 else None


def _estimate_audio_chunk_ms(audio_chunk: bytes | None, bytes_per_ms: float | None) -> int:
    if not audio_chunk or bytes_per_ms is None or bytes_per_ms <= 0:
        return 0
    return max(int(round(len(audio_chunk) / bytes_per_ms)), 1)


def _should_suppress_user_visible_event(event: RealtimeServerEvent) -> bool:
    return event.event_type in {
        "partial_text",
        "final_text",
        "audio_chunk",
        "audio_completed",
        "response_completed",
        "cancelled",
        "partial_transcript",
        "final_transcript",
        "tool_call",
    }


def _with_pending_response_metadata(
    event: RealtimeServerEvent | None,
    metadata: dict[str, str] | None,
) -> RealtimeServerEvent | None:
    if event is None or not metadata:
        return event
    if event.event_type not in {
        "partial_text",
        "final_text",
        "audio_chunk",
        "audio_completed",
        "tool_call",
        "cancelled",
        "response_completed",
    }:
        return event
    return event.model_copy(update={"metadata": dict(metadata)})


def _backlog_breach_event(
    *,
    provider: ProviderId,
    model: str,
    backlog_ms: int,
    backlog_budget_ms: int,
) -> RealtimeServerEvent:
    return RealtimeServerEvent(
        event_type="transport_backlog_budget_exceeded",
        provider=provider,
        model=model,
        text=f"backlog_ms={backlog_ms} backlog_budget_ms={backlog_budget_ms}",
    )


@dataclass(slots=True)
class _RealtimeTurnLog:
    turn_id: str
    audio_commit_received_at: str | None = None
    upstream_audio_commit_sent_at: str | None = None
    first_transcript_at: str | None = None
    first_partial_text_at: str | None = None
    first_audio_chunk_at: str | None = None
    outbound_audio_chunk_count: int = 0


class _RealtimeTurnLogTracker:
    def __init__(self) -> None:
        self.session_id: str | None = None
        self.trace_id: str | None = None
        self._turn_counter = 0
        self._turn: _RealtimeTurnLog | None = None

    def bind_event(self, event: RealtimeClientEvent) -> None:
        metadata = event.metadata or {}
        if self.session_id is None:
            self.session_id = metadata.get("session_id") or None
        if self.trace_id is None:
            self.trace_id = event.trace_id or metadata.get("trace_id") or None

    def observe_client_event(self, event: RealtimeClientEvent) -> None:
        self.bind_event(event)
        if event.event_type != "audio_commit":
            return

        turn_id = (event.metadata or {}).get("turn_id") or self._next_turn_id()
        if self._turn is not None and self._turn.turn_id != turn_id:
            self.finish_turn("superseded_by_new_commit")

        self._turn = _RealtimeTurnLog(turn_id=turn_id, audio_commit_received_at=_utc_now_iso())
        logger.info(
            "realtime.latency point=%s session_id=%s trace_id=%s turn_id=%s audio_commit_received_at=%s",
            "audio_commit_received",
            self.session_id,
            self.trace_id,
            turn_id,
            self._turn.audio_commit_received_at,
        )

    def observe_outbound_event(self, outbound: dict[str, Any]) -> None:
        outbound_type = outbound.get("type")
        if outbound_type == "input_audio_buffer.append" and self._turn is not None:
            self._turn.outbound_audio_chunk_count += 1
        if outbound_type == "input_audio_buffer.commit" and self._turn is not None and self._turn.upstream_audio_commit_sent_at is None:
            self._turn.upstream_audio_commit_sent_at = _utc_now_iso()
            logger.info(
                "realtime.latency point=%s session_id=%s trace_id=%s turn_id=%s upstream_audio_commit_sent_at=%s",
                "upstream_audio_commit_sent",
                self.session_id,
                self.trace_id,
                self._turn.turn_id,
                self._turn.upstream_audio_commit_sent_at,
            )

    def observe_server_event(self, event: RealtimeServerEvent) -> None:
        if self._turn is None:
            return

        if event.event_type in {"partial_transcript", "final_transcript"} and self._turn.first_transcript_at is None:
            self._turn.first_transcript_at = _utc_now_iso()
            logger.info(
                "realtime.latency point=%s session_id=%s trace_id=%s turn_id=%s first_transcript_at=%s",
                "first_transcript_at",
                self.session_id,
                self.trace_id,
                self._turn.turn_id,
                self._turn.first_transcript_at,
            )
        elif event.event_type == "partial_text" and self._turn.first_partial_text_at is None:
            self._turn.first_partial_text_at = _utc_now_iso()
            logger.info(
                "realtime.latency point=%s session_id=%s trace_id=%s turn_id=%s first_partial_text_at=%s",
                "first_partial_text_at",
                self.session_id,
                self.trace_id,
                self._turn.turn_id,
                self._turn.first_partial_text_at,
            )
        elif event.event_type == "audio_chunk" and self._turn.first_audio_chunk_at is None:
            self._turn.first_audio_chunk_at = _utc_now_iso()
            logger.info(
                "realtime.latency point=%s session_id=%s trace_id=%s turn_id=%s first_audio_chunk_at=%s",
                "first_audio_chunk_at",
                self.session_id,
                self.trace_id,
                self._turn.turn_id,
                self._turn.first_audio_chunk_at,
            )

        if event.event_type in {"audio_completed", "cancelled"}:
            self.finish_turn(event.event_type)

    def finish_turn(self, reason: str) -> None:
        if self._turn is None:
            return
        logger.info(
            "realtime.turn_summary reason=%s session_id=%s trace_id=%s turn_id=%s audio_commit_received_at=%s upstream_audio_commit_sent_at=%s first_transcript_at=%s first_partial_text_at=%s first_audio_chunk_at=%s outbound_audio_chunk_count=%s",
            reason,
            self.session_id,
            self.trace_id,
            self._turn.turn_id,
            self._turn.audio_commit_received_at,
            self._turn.upstream_audio_commit_sent_at,
            self._turn.first_transcript_at,
            self._turn.first_partial_text_at,
            self._turn.first_audio_chunk_at,
            self._turn.outbound_audio_chunk_count,
        )
        self._turn = None

    def _next_turn_id(self) -> str:
        self._turn_counter += 1
        return f"turn-{self._turn_counter:04d}"


def _terminal_server_events_for(
    event_type: str,
) -> set[str]:
    if event_type in {"session_start", "session_update"}:
        return {
            "session.created",
            "session.updated",
        }
    return {"response.done"}


class RealtimeSessionManager:
    def __init__(
        self,
        *,
        connection_factory: Callable[..., Awaitable[Any]] | None = None,
        policy: RealtimeSessionPolicy | None = None,
    ) -> None:
        self._connection_factory = connection_factory
        self.policy = policy or RealtimeSessionPolicy()

    def _connect(self, url: str, headers: dict[str, str]):
        connect = self._connection_factory or _load_websockets_connect()
        return connect(
            url,
            additional_headers=headers,
            ping_interval=self.policy.ping_interval_s,
            ping_timeout=self.policy.ping_timeout_s,
            close_timeout=self.policy.close_timeout_ms / 1000,
        )

    async def _receive_server_event(
        self, websocket: Any, config: RealtimeConnectionConfig
    ) -> dict[str, Any]:
        try:
            incoming_raw = await asyncio.wait_for(
                websocket.recv(),
                timeout=self.policy.response_timeout_ms / 1000,
            )
        except asyncio.TimeoutError as exc:
            raise GatewayError(
                GatewayErrorCode.PROVIDER_TIMEOUT,
                "Realtime provider response timed out.",
                provider=config.provider,
                model=config.model,
            ) from exc
        try:
            return json.loads(incoming_raw)
        except json.JSONDecodeError as exc:
            raise GatewayError(
                GatewayErrorCode.UPSTREAM_ERROR,
                "Realtime provider returned invalid JSON.",
                provider=config.provider,
                model=config.model,
            ) from exc

    async def _receive_server_event_with_timeout(
        self,
        websocket: Any,
        config: RealtimeConnectionConfig,
        timeout_ms: int,
    ) -> dict[str, Any] | None:
        try:
            incoming_raw = await asyncio.wait_for(
                websocket.recv(),
                timeout=timeout_ms / 1000,
            )
        except asyncio.TimeoutError:
            return None
        try:
            return json.loads(incoming_raw)
        except json.JSONDecodeError as exc:
            raise GatewayError(
                GatewayErrorCode.UPSTREAM_ERROR,
                "Realtime provider returned invalid JSON.",
                provider=config.provider,
                model=config.model,
            ) from exc

    async def _drain_stale_interrupt_tail(
        self,
        websocket: Any,
        config: RealtimeConnectionConfig,
    ) -> None:
        while True:
            incoming = await self._receive_server_event_with_timeout(
                websocket,
                config,
                self.policy.stale_interrupt_drain_ms,
            )
            if incoming is None:
                return
            if incoming.get("type") == "error":
                return
            if incoming.get("type") == "response.done":
                return

    async def _drain_server_events(
        self,
        websocket: Any,
        config: RealtimeConnectionConfig,
        state: RealtimeSessionState,
        tracker: _RealtimeTurnLogTracker,
        *,
        terminal_events: set[str],
    ) -> AsyncIterator[RealtimeServerEvent]:
        while state.awaiting_response:
            incoming = await self._receive_server_event(websocket, config)
            mapped = map_openai_event_to_server(
                incoming, provider=config.provider, model=config.model
            )
            if mapped is not None:
                tracker.observe_server_event(mapped)
                yield mapped
            if incoming.get("type") in terminal_events:
                state.awaiting_response = False
                tracker.finish_turn(incoming.get("type") or "terminal_event")
                break

    async def _close_websocket(self, websocket: Any) -> None:
        close = getattr(websocket, "close", None)
        if close is None:
            return
        with contextlib.suppress(Exception):
            await asyncio.wait_for(
                close(),
                timeout=self.policy.close_timeout_ms / 1000,
            )

    async def _send_outbound_message(
        self,
        websocket: Any,
        config: RealtimeConnectionConfig,
        tracker: _RealtimeTurnLogTracker,
        outbound: dict[str, Any],
    ) -> None:
        outbound_type = outbound.get("type")
        if outbound_type == "session.update":
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(
                    "realtime.outbound session.update provider=%s model=%s payload=%s",
                    config.provider,
                    config.model,
                    json.dumps(outbound, ensure_ascii=True),
                )
        elif outbound_type == "input_audio_buffer.append":
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(
                    "realtime.outbound input_audio_buffer.append provider=%s model=%s base64_chars=%s",
                    config.provider,
                    config.model,
                    len(outbound.get("audio") or ""),
                )
        elif outbound_type == "input_audio_buffer.commit":
            logger.debug(
                "realtime.outbound input_audio_buffer.commit provider=%s model=%s",
                config.provider,
                config.model,
            )

        tracker.observe_outbound_event(outbound)
        await websocket.send(json.dumps(outbound))

    async def stream(
        self,
        config: RealtimeConnectionConfig,
        events: AsyncIterator[RealtimeClientEvent],
    ) -> AsyncIterator[RealtimeServerEvent]:
        async with self._connect(config.url, config.headers) as websocket:
            state = RealtimeSessionState()
            tracker = _RealtimeTurnLogTracker()
            client_task: asyncio.Task[RealtimeClientEvent] | None = None
            server_task: asyncio.Task[dict[str, Any]] | None = None
            client_exhausted = False
            deferred_client_event: RealtimeClientEvent | None = None

            async def process_client_event(
                event: RealtimeClientEvent,
            ) -> RealtimeServerEvent | None:
                nonlocal client_exhausted
                tracker.observe_client_event(event)
                backlog_breach_event: RealtimeServerEvent | None = None
                if event.event_type == "session_start":
                    _configure_session_state(state, event)
                if event.event_type == "audio_chunk":
                    state.audio_buffer_open = True
                    state.backlog_ms += _estimate_audio_chunk_ms(
                        event.audio_chunk,
                        state.input_audio_bytes_per_ms,
                    )
                    if state.backlog_budget_ms and state.backlog_ms > state.backlog_budget_ms:
                        logger.warning(
                            "realtime.backpressure provider=%s model=%s backlog_ms=%s backlog_budget_ms=%s",
                            config.provider,
                            config.model,
                            state.backlog_ms,
                            state.backlog_budget_ms,
                        )
                        if not state.backlog_breach_reported:
                            state.backlog_breach_reported = True
                            backlog_breach_event = _backlog_breach_event(
                                provider=config.provider,
                                model=config.model,
                                backlog_ms=state.backlog_ms,
                                backlog_budget_ms=state.backlog_budget_ms,
                            )
                elif event.event_type == "audio_commit":
                    state.audio_buffer_open = False
                elif event.event_type == "close":
                    state.closed_by_client = True
                    client_exhausted = True

                outbound_messages = map_client_event_to_openai(event)
                if event.event_type in {"interrupt", "cancel"} and not state.awaiting_response:
                    outbound_messages = []

                for outbound in outbound_messages:
                    await self._send_outbound_message(websocket, config, tracker, outbound)

                if event_requires_server_drain(event.event_type):
                    state.awaiting_response = True
                    state.pending_event_type = event.event_type
                    state.pending_audio_completed = None
                    state.pending_response_metadata = dict(event.metadata or {})
                elif event.event_type in {"interrupt", "cancel"} and state.awaiting_response:
                    state.suppress_output_until_terminal = True

                return backlog_breach_event
            try:
                while True:
                    if (
                        state.stale_interrupt_tail_pending
                        and not state.awaiting_response
                        and not state.suppress_output_until_terminal
                    ):
                        await self._drain_stale_interrupt_tail(websocket, config)
                        state.stale_interrupt_tail_pending = False

                    if deferred_client_event is not None and not state.awaiting_response and not state.suppress_output_until_terminal:
                        backlog_breach_event = await process_client_event(deferred_client_event)
                        deferred_client_event = None
                        if backlog_breach_event is not None:
                            yield backlog_breach_event
                        continue

                    if client_task is None and deferred_client_event is None and not client_exhausted:
                        client_task = asyncio.create_task(
                            asyncio.wait_for(
                                anext(events),
                                timeout=self.policy.idle_timeout_ms / 1000,
                            )
                        )
                    if server_task is None and (
                        state.awaiting_response
                        or state.suppress_output_until_terminal
                    ):
                        server_task = asyncio.create_task(self._receive_server_event(websocket, config))

                    active_tasks = [task for task in (client_task, server_task) if task is not None]
                    if not active_tasks:
                        if state.audio_buffer_open and not state.awaiting_response and not state.closed_by_client:
                            await self._send_outbound_message(
                                websocket,
                                config,
                                tracker,
                                {"type": "input_audio_buffer.commit"},
                            )
                            state.audio_buffer_open = False
                            state.awaiting_response = True
                            state.pending_event_type = "audio_commit"
                            continue
                        break

                    done, _ = await asyncio.wait(active_tasks, return_when=asyncio.FIRST_COMPLETED)

                    if client_task in done:
                        try:
                            event = client_task.result()
                        except StopAsyncIteration:
                            client_exhausted = True
                            event = None
                        except asyncio.TimeoutError as exc:
                            raise GatewayError(
                                GatewayErrorCode.SESSION_CLOSED,
                                "Realtime session closed after idle timeout.",
                                provider=config.provider,
                                model=config.model,
                            ) from exc
                        finally:
                            client_task = None

                        if event is not None:
                            if state.awaiting_response and event.event_type not in {"interrupt", "cancel", "close"}:
                                deferred_client_event = event
                            else:
                                backlog_breach_event = await process_client_event(event)
                                if backlog_breach_event is not None:
                                    yield backlog_breach_event

                    if server_task in done:
                        incoming = server_task.result()
                        server_task = None
                        if (
                            state.suppress_output_until_terminal
                            and incoming.get("type") == "error"
                            and "no active response found"
                            in str((incoming.get("error") or {}).get("message") or "").lower()
                        ):
                            state.awaiting_response = False
                            state.pending_event_type = None
                            state.suppress_output_until_terminal = False
                            state.backlog_ms = 0
                            state.backlog_breach_reported = False
                            state.pending_audio_completed = None
                            state.pending_response_metadata = None
                            state.stale_interrupt_tail_pending = True
                            tracker.finish_turn("redundant_cancel_error")
                            continue

                        mapped = map_openai_event_to_server(
                            incoming,
                            provider=config.provider,
                            model=config.model,
                        )
                        mapped = _with_pending_response_metadata(
                            mapped,
                            state.pending_response_metadata,
                        )
                        if mapped is not None and mapped.event_type == "session_started":
                            if state.session_started_emitted:
                                mapped = None
                            else:
                                state.session_started_emitted = True
                        if mapped is not None and mapped.event_type == "audio_completed":
                            state.pending_audio_completed = mapped
                            mapped = None

                        terminal_events = _terminal_server_events_for(
                            state.pending_event_type or "close",
                        )
                        if (
                            incoming.get("type") in terminal_events
                            and state.pending_audio_completed is not None
                            and not state.suppress_output_until_terminal
                        ):
                            tracker.observe_server_event(state.pending_audio_completed)
                            yield state.pending_audio_completed
                            state.pending_audio_completed = None

                        if mapped is not None:
                            tracker.observe_server_event(mapped)
                            if not (
                                state.suppress_output_until_terminal
                                and _should_suppress_user_visible_event(mapped)
                            ):
                                yield mapped

                        if incoming.get("type") in terminal_events:
                            state.awaiting_response = False
                            state.pending_event_type = None
                            state.suppress_output_until_terminal = False
                            state.backlog_ms = 0
                            state.backlog_breach_reported = False
                            state.pending_audio_completed = None
                            state.pending_response_metadata = None
                            tracker.finish_turn(incoming.get("type") or "terminal_event")

                    if (
                        client_exhausted
                        and state.closed_by_client
                        and not state.audio_buffer_open
                        and not state.awaiting_response
                        and not state.suppress_output_until_terminal
                    ):
                        break
            finally:
                for task in (client_task, server_task):
                    if task is not None and not task.done():
                        task.cancel()
                        with contextlib.suppress(asyncio.CancelledError):
                            await task
                tracker.finish_turn("session_closed")
                await self._close_websocket(websocket)


class OpenAIRealtimeAdapter(RealtimeAdapter):
    def __init__(
        self,
        *,
        provider: ProviderId,
        secrets: ProviderConfig,
        session_manager: RealtimeSessionManager | None = None,
    ) -> None:
        self.provider = provider
        self.secrets = secrets
        self.session_manager = session_manager or RealtimeSessionManager()

    async def session(
        self,
        events: AsyncIterator[RealtimeClientEvent],
        runtime_config: RuntimeProviderConfig,
    ) -> AsyncIterator[RealtimeServerEvent]:
        first_event: RealtimeClientEvent | None = None
        async for event in events:
            first_event = event
            break
        if first_event is None:
            return
        model = first_event.model or ""
        secrets = resolve_provider_secrets(self.secrets, runtime_config)
        config = RealtimeConnectionConfig(
            provider=self.provider,
            model=model,
            url=build_openai_realtime_url(secrets, model),
            headers=build_openai_realtime_headers(secrets),
        )

        async def chained_events() -> AsyncIterator[RealtimeClientEvent]:
            yield first_event
            async for event in events:
                yield event

        async for event in self.session_manager.stream(config, chained_events()):
            yield event
