from __future__ import annotations

import asyncio
import json
import sys
from collections.abc import AsyncIterator
from pathlib import Path

import pytest

SOURCE_ROOT = Path(__file__).resolve().parents[1] / "src"
resolved_source_root = str(SOURCE_ROOT)
if resolved_source_root in sys.path:
    sys.path.remove(resolved_source_root)
sys.path.insert(0, resolved_source_root)

from llm_gateway.config import ProviderConfig
from llm_gateway.errors import GatewayError
from llm_gateway.models import ProviderId, RealtimeClientEvent
from llm_gateway.provider_runtime import RuntimeProviderConfig
from llm_gateway.providers.openai.realtime import (
    OpenAIRealtimeAdapter,
    RealtimeConnectionConfig,
    RealtimeSessionManager,
    RealtimeSessionPolicy,
    build_openai_realtime_headers,
    build_openai_realtime_url,
    event_requires_server_drain,
    map_client_event_to_openai,
    map_openai_event_to_server,
)


class FakeWebSocket:
    def __init__(self, incoming_messages: list[dict]) -> None:
        self.incoming_messages = [json.dumps(item) for item in incoming_messages]
        self.sent_messages: list[dict] = []
        self.closed = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def send(self, payload: str) -> None:
        self.sent_messages.append(json.loads(payload))

    async def recv(self) -> str:
        return self.incoming_messages.pop(0)

    async def close(self) -> None:
        self.closed = True


class ControlFirstFakeWebSocket(FakeWebSocket):
    def __init__(self) -> None:
        super().__init__([
            {"type": "session.created"},
            {"type": "session.updated"},
        ])
        self._cancel_sent = asyncio.Event()
        self._post_cancel_messages = [
            json.dumps(
                {
                    "type": "response.audio.delta",
                    "delta": "AQI=",
                    "mime_type": "audio/pcm",
                    "sequence_number": 1,
                }
            ),
            json.dumps({"type": "response.done", "response": {"status": "cancelled"}}),
        ]

    async def send(self, payload: str) -> None:
        await super().send(payload)
        if self.sent_messages[-1]["type"] == "response.cancel":
            self._cancel_sent.set()

    async def recv(self) -> str:
        if self.incoming_messages:
            return await super().recv()
        await asyncio.wait_for(self._cancel_sent.wait(), timeout=0.2)
        return self._post_cancel_messages.pop(0)


class CancelErrorAfterInterruptWebSocket(FakeWebSocket):
    def __init__(self) -> None:
        super().__init__([
            {"type": "session.created"},
            {"type": "session.updated"},
        ])
        self._cancel_sent = asyncio.Event()

    async def send(self, payload: str) -> None:
        await super().send(payload)
        if self.sent_messages[-1]["type"] == "response.cancel":
            self._cancel_sent.set()

    async def recv(self) -> str:
        if self.incoming_messages:
            return await super().recv()
        await asyncio.wait_for(self._cancel_sent.wait(), timeout=0.2)
        return json.dumps(
            {
                "type": "error",
                "error": {
                    "message": "Cancellation failed: no active response found",
                },
            }
        )


class CancelErrorThenLateDoneWebSocket(FakeWebSocket):
    def __init__(self) -> None:
        super().__init__([
            {"type": "session.created"},
            {"type": "session.updated"},
        ])
        self._cancel_sent = asyncio.Event()
        self._post_cancel_messages = [
            json.dumps(
                {
                    "type": "error",
                    "error": {
                        "message": "Cancellation failed: no active response found",
                    },
                }
            ),
            json.dumps(
                {
                    "type": "response.done",
                    "response": {
                        "status": "completed",
                        "usage": {"input_tokens": 3, "output_tokens": 1},
                    },
                }
            ),
            json.dumps({"type": "response.text.done", "text": "new answer"}),
            json.dumps(
                {
                    "type": "response.done",
                    "response": {
                        "status": "completed",
                        "usage": {"input_tokens": 5, "output_tokens": 7},
                    },
                }
            ),
        ]

    async def send(self, payload: str) -> None:
        await super().send(payload)
        if self.sent_messages[-1]["type"] == "response.cancel":
            self._cancel_sent.set()

    async def recv(self) -> str:
        if self.incoming_messages:
            return await super().recv()
        await asyncio.wait_for(self._cancel_sent.wait(), timeout=0.2)
        return self._post_cancel_messages.pop(0)


class DeferredAudioCommitRaceWebSocket(FakeWebSocket):
    def __init__(self) -> None:
        super().__init__([
            {"type": "session.created"},
            {"type": "session.updated"},
        ])
        self._cancel_sent = asyncio.Event()
        self._cancel_terminal_sent = False
        self._followup_response_sent = False

    async def send(self, payload: str) -> None:
        await super().send(payload)
        if self.sent_messages[-1]["type"] == "response.cancel":
            self._cancel_sent.set()

    async def recv(self) -> str:
        if self.incoming_messages:
            return await super().recv()

        await asyncio.wait_for(self._cancel_sent.wait(), timeout=0.2)

        if not self._cancel_terminal_sent:
            await asyncio.sleep(0.05)
            self._cancel_terminal_sent = True
            return json.dumps({"type": "response.done", "response": {"status": "cancelled"}})

        if not self._followup_response_sent:
            self._followup_response_sent = True
            return json.dumps(
                {
                    "type": "conversation.item.input_audio_transcription.completed",
                    "transcript": "again",
                }
            )

        return json.dumps(
            {
                "type": "response.done",
                "response": {
                    "status": "completed",
                    "usage": {"input_tokens": 5, "output_tokens": 3},
                },
            }
        )


class CancelErrorThenDeferredLateDoneWebSocket(FakeWebSocket):
    def __init__(self) -> None:
        super().__init__([
            {"type": "session.created"},
            {"type": "session.updated"},
        ])
        self._cancel_sent = asyncio.Event()
        self.error_emitted = asyncio.Event()
        self._post_cancel_messages = [
            json.dumps(
                {
                    "type": "error",
                    "error": {
                        "message": "Cancellation failed: no active response found",
                    },
                }
            ),
            json.dumps(
                {
                    "type": "response.done",
                    "response": {
                        "status": "completed",
                        "usage": {"input_tokens": 2, "output_tokens": 1},
                    },
                }
            ),
            json.dumps({"type": "response.text.done", "text": "fresh answer"}),
            json.dumps(
                {
                    "type": "response.done",
                    "response": {
                        "status": "completed",
                        "usage": {"input_tokens": 4, "output_tokens": 6},
                    },
                }
            ),
        ]

    async def send(self, payload: str) -> None:
        await super().send(payload)
        if self.sent_messages[-1]["type"] == "response.cancel":
            self._cancel_sent.set()

    async def recv(self) -> str:
        if self.incoming_messages:
            return await super().recv()
        await asyncio.wait_for(self._cancel_sent.wait(), timeout=0.2)
        message = self._post_cancel_messages.pop(0)
        payload = json.loads(message)
        if payload.get("type") == "error":
            self.error_emitted.set()
        return message


class CancelErrorThenDeferredLateAudioWebSocket(FakeWebSocket):
    def __init__(self) -> None:
        super().__init__([
            {"type": "session.created"},
            {"type": "session.updated"},
        ])
        self._cancel_sent = asyncio.Event()
        self.error_emitted = asyncio.Event()
        self._post_cancel_messages = [
            json.dumps(
                {
                    "type": "error",
                    "error": {
                        "message": "Cancellation failed: no active response found",
                    },
                }
            ),
            json.dumps(
                {
                    "type": "response.audio.delta",
                    "delta": "AQI=",
                    "mime_type": "audio/pcm",
                    "sequence_number": 1,
                }
            ),
            json.dumps(
                {
                    "type": "response.done",
                    "response": {
                        "status": "completed",
                        "usage": {"input_tokens": 2, "output_tokens": 1},
                    },
                }
            ),
            json.dumps({"type": "response.text.done", "text": "fresh answer"}),
            json.dumps(
                {
                    "type": "response.done",
                    "response": {
                        "status": "completed",
                        "usage": {"input_tokens": 4, "output_tokens": 6},
                    },
                }
            ),
        ]

    async def send(self, payload: str) -> None:
        await super().send(payload)
        if self.sent_messages[-1]["type"] == "response.cancel":
            self._cancel_sent.set()

    async def recv(self) -> str:
        if self.incoming_messages:
            return await super().recv()
        await asyncio.wait_for(self._cancel_sent.wait(), timeout=0.2)
        message = self._post_cancel_messages.pop(0)
        payload = json.loads(message)
        if payload.get("type") == "error":
            self.error_emitted.set()
        return message


class CompletedResponseThenCancelErrorWebSocket(FakeWebSocket):
    def __init__(self) -> None:
        super().__init__(
            [
                {"type": "session.created"},
                {"type": "session.updated"},
                {
                    "type": "response.done",
                    "response": {
                        "status": "completed",
                        "usage": {"input_tokens": 3, "output_tokens": 2},
                    },
                },
            ]
        )
        self._cancel_sent = asyncio.Event()
        self._follow_up_requested = asyncio.Event()
        self.response_done_emitted = asyncio.Event()
        self._error_message = json.dumps(
            {
                "type": "error",
                "error": {
                    "message": "Cancellation failed: no active response found",
                },
            }
        )
        self._follow_up_messages = [
            json.dumps({"type": "response.text.done", "text": "follow-up answer"}),
            json.dumps(
                {
                    "type": "response.done",
                    "response": {
                        "status": "completed",
                        "usage": {"input_tokens": 5, "output_tokens": 4},
                    },
                }
            ),
        ]

    async def send(self, payload: str) -> None:
        await super().send(payload)
        message_type = self.sent_messages[-1]["type"]
        if message_type == "response.cancel":
            self._cancel_sent.set()
        elif message_type == "response.create" and not self.incoming_messages:
            self._follow_up_requested.set()

    async def recv(self) -> str:
        if self.incoming_messages:
            message = await super().recv()
            payload = json.loads(message)
            if payload.get("type") == "response.done":
                self.response_done_emitted.set()
            return message
        if self._follow_up_requested.is_set():
            if self._cancel_sent.is_set():
                self._cancel_sent.clear()
                return self._error_message
            if self._follow_up_messages:
                return self._follow_up_messages.pop(0)
        return await super().recv()


class GuardedSessionStartWebSocket(FakeWebSocket):
    def __init__(self) -> None:
        super().__init__(
            [
                {"type": "session.created"},
                {
                    "type": "response.done",
                    "response": {
                        "status": "completed",
                        "usage": {"input_tokens": 1, "output_tokens": 1},
                    },
                },
            ]
        )
        self.session_created_emitted = False

    async def send(self, payload: str) -> None:
        message = json.loads(payload)
        if not self.session_created_emitted and message["type"] != "session.update":
            raise AssertionError(
                f"sent {message['type']} before session_start drain completed"
            )
        self.sent_messages.append(message)

    async def recv(self) -> str:
        if not self.session_created_emitted:
            await asyncio.sleep(0.01)
        incoming = await super().recv()
        payload = json.loads(incoming)
        if payload.get("type") == "session.created":
            self.session_created_emitted = True
        return incoming


class GuardedSessionUpdatedWebSocket(FakeWebSocket):
    def __init__(self) -> None:
        super().__init__(
            [
                {"type": "session.created"},
                {"type": "session.updated"},
                {
                    "type": "response.done",
                    "response": {
                        "status": "completed",
                        "usage": {"input_tokens": 1, "output_tokens": 1},
                    },
                },
            ]
        )
        self.session_updated_emitted = False

    async def send(self, payload: str) -> None:
        message = json.loads(payload)
        if not self.session_updated_emitted and message["type"] != "session.update":
            raise AssertionError(
                f"sent {message['type']} before session.updated drain completed"
            )
        self.sent_messages.append(message)

    async def recv(self) -> str:
        if not self.session_updated_emitted:
            await asyncio.sleep(0.01)
        incoming = await super().recv()
        payload = json.loads(incoming)
        if payload.get("type") == "session.updated":
            self.session_updated_emitted = True
        return incoming


class FakeConnectionFactory:
    def __init__(self, websocket: FakeWebSocket) -> None:
        self.websocket = websocket
        self.calls: list[tuple[str, dict[str, str], dict[str, object]]] = []

    def __call__(self, url: str, additional_headers: dict[str, str], **kwargs):
        self.calls.append((url, additional_headers, kwargs))
        return self.websocket


@pytest.mark.asyncio
class TestRealtimeAdapter:
    async def test_realtime_session_manager_connects_with_explicit_keepalive_policy(self):
        websocket = FakeWebSocket([
            {"type": "session.created"},
            {"type": "session.updated"},
        ])
        factory = FakeConnectionFactory(websocket)
        policy = RealtimeSessionPolicy(
            ping_interval_s=15.0,
            ping_timeout_s=90.0,
            close_timeout_ms=2_500,
        )
        manager = RealtimeSessionManager(connection_factory=factory, policy=policy)
        config = RealtimeConnectionConfig(
            provider=ProviderId.OPENAI,
            model="gpt-realtime",
            url="wss://example/realtime?model=gpt-realtime",
            headers={"Authorization": "Bearer token"},
        )

        async def events() -> AsyncIterator[RealtimeClientEvent]:
            yield RealtimeClientEvent(event_type="session_start", model="gpt-realtime")
            yield RealtimeClientEvent(event_type="close", model="gpt-realtime")

        output = [event async for event in manager.stream(config, events())]

        assert [event.event_type for event in output] == ["session_started"]
        assert len(factory.calls) == 1
        _, _, kwargs = factory.calls[0]
        assert kwargs["ping_interval"] == 15.0
        assert kwargs["ping_timeout"] == 90.0
        assert kwargs["close_timeout"] == 2.5

    async def test_client_event_text_maps_to_conversation_and_response(self):
        events = map_client_event_to_openai(
            RealtimeClientEvent(event_type="text", model="gpt-4o-mini", text="hello")
        )
        assert events[0]["type"] == "conversation.item.create"
        assert events[1]["type"] == "response.create"

    async def test_openai_delta_maps_to_partial_text(self):
        event = map_openai_event_to_server(
            {"type": "response.text.delta", "delta": "he"},
            provider=ProviderId.OPENAI,
            model="gpt-4o-mini",
        )
        assert event.event_type == "partial_text"
        assert event.text == "he"

    async def test_audio_transcription_completed_maps_to_final_transcript(self):
        event = map_openai_event_to_server(
            {
                "type": "conversation.item.audio_transcription.completed",
                "transcript": "你好",
            },
            provider=ProviderId.OPENAI,
            model="gpt-realtime",
        )
        assert event.event_type == "final_transcript"
        assert event.transcript == "你好"

    async def test_response_done_maps_usage_to_response_completed(self):
        event = map_openai_event_to_server(
            {
                "type": "response.done",
                "response": {
                    "status": "completed",
                    "usage": {
                        "input_tokens": 7,
                        "output_tokens": 5,
                    },
                },
            },
            provider=ProviderId.OPENAI,
            model="gpt-4o-mini",
        )
        assert event is not None
        assert event.event_type == "response_completed"
        assert event.usage is not None
        assert event.usage.input_tokens == 7
        assert event.usage.output_tokens == 5
        assert event.usage.total_tokens == 12

    async def test_openai_audio_delta_maps_to_audio_chunk(self):
        event = map_openai_event_to_server(
            {
                "type": "response.audio.delta",
                "delta": "AQI=",
                "mime_type": "audio/pcm",
                "sequence_number": 3,
            },
            provider=ProviderId.OPENAI,
            model="gpt-4o-mini",
        )
        assert event.event_type == "audio_chunk"
        assert event.audio_chunk == b"\x01\x02"
        assert event.mime_type == "audio/pcm"
        assert event.sequence == 3

    async def test_realtime_function_call_done_maps_to_tool_call(self):
        event = map_openai_event_to_server(
            {
                "type": "response.output_item.done",
                "item": {
                    "type": "function_call",
                    "name": "delegate_to_agent_runtime",
                    "call_id": "call-weather-1",
                    "arguments": '{"user_text":"广州明天的天气","reason":"weather"}',
                },
            },
            provider=ProviderId.OPENAI,
            model="gpt-realtime",
        )

        assert event is not None
        assert event.event_type == "tool_call"
        assert event.tool_name == "delegate_to_agent_runtime"
        assert event.tool_call_id == "call-weather-1"
        assert event.tool_arguments == {"user_text": "广州明天的天气", "reason": "weather"}

    async def test_realtime_function_call_arguments_done_without_name_is_ignored(self):
        event = map_openai_event_to_server(
            {
                "type": "response.function_call_arguments.done",
                "call_id": "call-weather-1",
                "arguments": '{"user_text":"广州明天的天气"}',
            },
            provider=ProviderId.OPENAI,
            model="gpt-realtime",
        )

        assert event is None

    async def test_session_start_can_request_audio_output(self):
        events = map_client_event_to_openai(
            RealtimeClientEvent(
                event_type="session_start",
                model="gpt-4o-mini",
                metadata={"session_type": "realtime", "output_audio": "true", "voice": "alloy"},
            )
        )
        assert events[0]["session"]["type"] == "realtime"
        assert events[0]["session"]["voice"] == "alloy"
        assert events[0]["session"]["modalities"] == ["text", "audio"]

    async def test_session_start_can_expose_exact_realtime_tools(self):
        delegation_tool = {
            "type": "function",
            "name": "delegate_to_agent_runtime",
            "description": "Delegate governed business questions to AgentRuntime.",
            "parameters": {
                "type": "object",
                "properties": {"user_text": {"type": "string"}},
                "required": ["user_text"],
            },
        }

        events = map_client_event_to_openai(
            RealtimeClientEvent(
                event_type="session_start",
                model="gpt-realtime",
                metadata={"session_type": "realtime"},
                tools=[delegation_tool],
                tool_choice="auto",
            )
        )

        assert events[0]["session"]["tools"] == [delegation_tool]
        assert events[0]["session"]["tool_choice"] == "auto"

    async def test_session_start_supports_transcription_settings_without_modalities(self):
        events = map_client_event_to_openai(
            RealtimeClientEvent(
                event_type="session_start",
                model="gpt-4o-mini-transcribe",
                metadata={
                    "session_type": "realtime",
                    "input_audio_transcription_model": "gpt-4o-mini-transcribe",
                    "input_audio_format": "audio/pcm",
                },
            )
        )
        assert events[0]["session"]["type"] == "realtime"
        assert events[0]["session"]["input_audio_transcription"]["model"] == "gpt-4o-mini-transcribe"
        assert events[0]["session"]["input_audio_format"] == "pcm16"

    async def test_input_audio_buffer_speech_started_maps_to_provider_state_change(self):
        event = map_openai_event_to_server(
            {"type": "input_audio_buffer.speech_started"},
            ProviderId.OPENAI,
            "gpt-realtime",
        )

        assert event is not None
        assert event.event_type == "state_changed"
        assert event.state == "provider_speech_started"

    async def test_transcription_commit_does_not_create_model_response(self):
        events = map_client_event_to_openai(
            RealtimeClientEvent(
                event_type="audio_commit",
                model="gpt-4o-mini-transcribe",
                metadata={"transcription_only": "true"},
            )
        )
        assert events == [{"type": "input_audio_buffer.commit"}]

    async def test_realtime_generated_transcript_commit_creates_text_response(self):
        events = map_client_event_to_openai(
            RealtimeClientEvent(
                event_type="audio_commit",
                provider=ProviderId.OPENAI,
                model="gpt-realtime",
                metadata={
                    "transcription_only": "true",
                    "realtime_generated_transcript": "true",
                    "output_audio": "false",
                    "instructions": "transcribe only",
                },
            )
        )
        assert events == [
            {"type": "input_audio_buffer.commit"},
            {
                "type": "response.create",
                "response": {"instructions": "transcribe only", "modalities": ["text"]},
            },
        ]

    async def test_text_response_can_carry_turn_specific_instructions(self):
        events = map_client_event_to_openai(
            RealtimeClientEvent(
                event_type="text",
                model="gpt-realtime",
                text="User said: hello",
                metadata={"instructions": "acknowledge only"},
            )
        )
        assert events == [
            {
                "type": "conversation.item.create",
                "item": {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": "User said: hello"}],
                },
            },
            {"type": "response.create", "response": {"instructions": "acknowledge only"}},
        ]

    async def test_tool_result_maps_to_function_call_output_and_followup_response(self):
        events = map_client_event_to_openai(
            RealtimeClientEvent(
                event_type="tool_result",
                model="gpt-realtime",
                tool_call_id="call-weather-1",
                tool_output="广州明天小雨，22 到 28 摄氏度。",
                metadata={"instructions": "Speak the tool output to the caller."},
            )
        )

        assert events == [
            {
                "type": "conversation.item.create",
                "item": {
                    "type": "function_call_output",
                    "call_id": "call-weather-1",
                    "output": "广州明天小雨，22 到 28 摄氏度。",
                },
            },
            {
                "type": "response.create",
                "response": {"instructions": "Speak the tool output to the caller."},
            },
        ]

    async def test_audio_chunk_does_not_require_server_drain(self):
        assert not event_requires_server_drain("audio_chunk")
        assert event_requires_server_drain("text")
        assert event_requires_server_drain("tool_result")

    async def test_interrupt_and_cancel_do_not_require_server_drain(self):
        assert not event_requires_server_drain("interrupt")
        assert not event_requires_server_drain("cancel")

    async def test_realtime_session_manager_skips_recv_for_audio_append(self):
        websocket = FakeWebSocket(
            [
                {"type": "session.created"},
                {"type": "response.text.done", "text": "ok"},
                {
                    "type": "response.done",
                    "response": {
                        "status": "completed",
                        "usage": {"input_tokens": 3, "output_tokens": 2},
                    },
                },
            ]
        )
        factory = FakeConnectionFactory(websocket)
        manager = RealtimeSessionManager(connection_factory=factory)
        config = RealtimeConnectionConfig(
            provider=ProviderId.OPENAI,
            model="gpt-4o-mini",
            url="wss://example/realtime?model=gpt-4o-mini",
            headers={"Authorization": "Bearer token"},
        )

        async def events() -> AsyncIterator[RealtimeClientEvent]:
            yield RealtimeClientEvent(event_type="session_start", model="gpt-4o-mini")
            yield RealtimeClientEvent(
                event_type="audio_chunk", model="gpt-4o-mini", audio_chunk=b"\x01\x02"
            )
            yield RealtimeClientEvent(event_type="text", model="gpt-4o-mini", text="hi")
            yield RealtimeClientEvent(event_type="close", model="gpt-4o-mini")

        output = [event async for event in manager.stream(config, events())]
        assert output[0].event_type == "session_started"
        assert output[1].event_type == "final_text"
        assert output[2].event_type == "response_completed"
        assert output[2].usage is not None
        assert output[2].usage.total_tokens == 5
        assert len(websocket.sent_messages) == 4
        assert websocket.closed

    async def test_realtime_session_manager_tags_server_events_with_pending_response_metadata(self):
        websocket = FakeWebSocket(
            [
                {"type": "session.created"},
                {"type": "input_audio_buffer.speech_started"},
                {"type": "response.text.delta", "delta": "hello"},
                {"type": "response.audio.delta", "delta": "AQI=", "mime_type": "audio/pcm"},
                {"type": "response.done", "response": {"status": "completed"}},
            ]
        )
        factory = FakeConnectionFactory(websocket)
        manager = RealtimeSessionManager(connection_factory=factory)
        config = RealtimeConnectionConfig(
            provider=ProviderId.OPENAI,
            model="gpt-realtime",
            url="wss://example/realtime?model=gpt-realtime",
            headers={"Authorization": "Bearer token"},
        )

        async def events() -> AsyncIterator[RealtimeClientEvent]:
            yield RealtimeClientEvent(event_type="session_start", model="gpt-realtime")
            yield RealtimeClientEvent(
                event_type="text",
                model="gpt-realtime",
                text="greet",
                metadata={
                    "turn_id": "turn-greeting",
                    "generation_id": "generation-greeting",
                    "realtime_response_purpose": "greeting",
                },
            )
            yield RealtimeClientEvent(
                event_type="audio_chunk",
                model="gpt-realtime",
                audio_chunk=b"caller",
                metadata={
                    "turn_id": "turn-caller",
                    "generation_id": "generation-caller",
                },
            )
            yield RealtimeClientEvent(event_type="close", model="gpt-realtime")

        output = [event async for event in manager.stream(config, events())]

        user_visible = [event for event in output if event.event_type in {"partial_text", "audio_chunk"}]
        assert [event.metadata.get("realtime_response_purpose") for event in user_visible] == [
            "greeting",
            "greeting",
        ]
        assert [event.metadata.get("turn_id") for event in user_visible] == [
            "turn-greeting",
            "turn-greeting",
        ]
        state_events = [event for event in output if event.event_type == "state_changed"]
        assert state_events
        assert all(not event.metadata for event in state_events)

    async def test_realtime_session_manager_commits_buffer_on_half_close(self):
        websocket = FakeWebSocket(
            [
                {"type": "session.created"},
                {"type": "conversation.item.input_audio_transcription.completed", "transcript": "hello"},
                {
                    "type": "response.done",
                    "response": {
                        "status": "completed",
                        "usage": {"input_tokens": 6, "output_tokens": 1},
                    },
                },
            ]
        )
        factory = FakeConnectionFactory(websocket)
        manager = RealtimeSessionManager(connection_factory=factory)
        config = RealtimeConnectionConfig(
            provider=ProviderId.OPENAI,
            model="gpt-4o-mini-transcribe",
            url="wss://example/realtime?model=gpt-4o-mini-transcribe",
            headers={"Authorization": "Bearer token"},
        )

        async def events() -> AsyncIterator[RealtimeClientEvent]:
            yield RealtimeClientEvent(event_type="session_start", model="gpt-4o-mini-transcribe")
            yield RealtimeClientEvent(
                event_type="audio_chunk",
                model="gpt-4o-mini-transcribe",
                audio_chunk=b"\x01\x02",
            )

        output = [event async for event in manager.stream(config, events())]
        assert output[-2].event_type == "final_transcript"
        assert output[-1].event_type == "response_completed"
        assert websocket.sent_messages[-1]["type"] == "input_audio_buffer.commit"

    async def test_realtime_session_manager_does_not_forward_stale_audio_after_interrupt(self):
        websocket = FakeWebSocket(
            [
                {"type": "session.created"},
                {"type": "response.audio.delta", "delta": "AQI=", "mime_type": "audio/pcm", "sequence_number": 1},
                {"type": "response.done", "response": {"status": "cancelled"}},
            ]
        )
        factory = FakeConnectionFactory(websocket)
        manager = RealtimeSessionManager(connection_factory=factory)
        config = RealtimeConnectionConfig(
            provider=ProviderId.OPENAI,
            model="gpt-4o-mini",
            url="wss://example/realtime?model=gpt-4o-mini",
            headers={"Authorization": "Bearer token"},
        )

        async def events() -> AsyncIterator[RealtimeClientEvent]:
            yield RealtimeClientEvent(event_type="session_start", model="gpt-4o-mini")
            yield RealtimeClientEvent(event_type="interrupt", model="gpt-4o-mini")
            yield RealtimeClientEvent(event_type="close", model="gpt-4o-mini")

        output = [event async for event in manager.stream(config, events())]

        assert [event.event_type for event in output] == ["session_started"]
        assert websocket.sent_messages[1]["type"] == "response.cancel"

    async def test_realtime_session_manager_surfaces_backlog_budget_breach_without_suppressing_audio(self):
        websocket = FakeWebSocket(
            [
                {"type": "session.created"},
                {"type": "response.audio.delta", "delta": "AQI=", "mime_type": "audio/pcm", "sequence_number": 1},
                {
                    "type": "response.done",
                    "response": {
                        "status": "completed",
                        "usage": {"input_tokens": 3, "output_tokens": 1},
                    },
                },
            ]
        )
        factory = FakeConnectionFactory(websocket)
        manager = RealtimeSessionManager(connection_factory=factory)
        config = RealtimeConnectionConfig(
            provider=ProviderId.OPENAI,
            model="gpt-4o-mini",
            url="wss://example/realtime?model=gpt-4o-mini",
            headers={"Authorization": "Bearer token"},
        )

        async def events() -> AsyncIterator[RealtimeClientEvent]:
            yield RealtimeClientEvent(
                event_type="session_start",
                model="gpt-4o-mini",
                metadata={
                    "backlog_budget_ms": "1",
                    "input_audio_format": "audio/pcm",
                    "input_audio_sample_rate_hz": "16000",
                    "input_audio_channels": "1",
                },
            )
            yield RealtimeClientEvent(
                event_type="audio_chunk",
                model="gpt-4o-mini",
                audio_chunk=b"\x00" * 128,
            )
            yield RealtimeClientEvent(event_type="audio_commit", model="gpt-4o-mini")
            yield RealtimeClientEvent(event_type="close", model="gpt-4o-mini")

        output = [event async for event in manager.stream(config, events())]

        event_types = [event.event_type for event in output]
        assert "session_started" in event_types
        assert "transport_backlog_budget_exceeded" in event_types
        assert "audio_chunk" in event_types
        assert "response_completed" in event_types
        assert event_types.index("transport_backlog_budget_exceeded") < event_types.index("audio_chunk")
        backlog_event = next(event for event in output if event.event_type == "transport_backlog_budget_exceeded")
        audio_event = next(event for event in output if event.event_type == "audio_chunk")
        assert backlog_event.text == "backlog_ms=4 backlog_budget_ms=1"
        assert audio_event.audio_chunk == b"\x01\x02"

    async def test_realtime_session_manager_sends_interrupt_before_response_done_drain(self):
        websocket = ControlFirstFakeWebSocket()
        factory = FakeConnectionFactory(websocket)
        manager = RealtimeSessionManager(
            connection_factory=factory,
            policy=RealtimeSessionPolicy(response_timeout_ms=250),
        )
        config = RealtimeConnectionConfig(
            provider=ProviderId.OPENAI,
            model="gpt-4o-mini",
            url="wss://example/realtime?model=gpt-4o-mini",
            headers={"Authorization": "Bearer token"},
        )

        async def events() -> AsyncIterator[RealtimeClientEvent]:
            yield RealtimeClientEvent(event_type="session_start", model="gpt-4o-mini")
            yield RealtimeClientEvent(event_type="text", model="gpt-4o-mini", text="hello")
            yield RealtimeClientEvent(event_type="interrupt", model="gpt-4o-mini")
            yield RealtimeClientEvent(event_type="close", model="gpt-4o-mini")

        output = [event async for event in manager.stream(config, events())]

        assert [message["type"] for message in websocket.sent_messages] == [
            "session.update",
            "conversation.item.create",
            "response.create",
            "response.cancel",
        ]
        assert [event.event_type for event in output] == ["session_started"]

    async def test_realtime_session_manager_treats_redundant_cancel_error_as_terminal_after_interrupt(self):
        websocket = CancelErrorAfterInterruptWebSocket()
        factory = FakeConnectionFactory(websocket)
        manager = RealtimeSessionManager(
            connection_factory=factory,
            policy=RealtimeSessionPolicy(response_timeout_ms=250),
        )
        config = RealtimeConnectionConfig(
            provider=ProviderId.OPENAI,
            model="gpt-realtime",
            url="wss://example/realtime?model=gpt-realtime",
            headers={"Authorization": "Bearer token"},
        )

        async def events() -> AsyncIterator[RealtimeClientEvent]:
            yield RealtimeClientEvent(event_type="session_start", model="gpt-realtime")
            yield RealtimeClientEvent(event_type="text", model="gpt-realtime", text="hello")
            yield RealtimeClientEvent(event_type="interrupt", model="gpt-realtime")
            yield RealtimeClientEvent(event_type="close", model="gpt-realtime")

        output = [event async for event in manager.stream(config, events())]

        assert [message["type"] for message in websocket.sent_messages] == [
            "session.update",
            "conversation.item.create",
            "response.create",
            "response.cancel",
        ]
        assert [event.event_type for event in output] == ["session_started"]

    async def test_realtime_session_manager_ignores_late_terminal_from_interrupted_turn(self):
        websocket = CancelErrorThenLateDoneWebSocket()
        factory = FakeConnectionFactory(websocket)
        manager = RealtimeSessionManager(
            connection_factory=factory,
            policy=RealtimeSessionPolicy(response_timeout_ms=250),
        )
        config = RealtimeConnectionConfig(
            provider=ProviderId.OPENAI,
            model="gpt-realtime",
            url="wss://example/realtime?model=gpt-realtime",
            headers={"Authorization": "Bearer token"},
        )

        async def events() -> AsyncIterator[RealtimeClientEvent]:
            yield RealtimeClientEvent(event_type="session_start", model="gpt-realtime")
            yield RealtimeClientEvent(event_type="text", model="gpt-realtime", text="hello")
            yield RealtimeClientEvent(event_type="interrupt", model="gpt-realtime")
            yield RealtimeClientEvent(event_type="text", model="gpt-realtime", text="again")
            yield RealtimeClientEvent(event_type="close", model="gpt-realtime")

        output = [event async for event in manager.stream(config, events())]

        assert [message["type"] for message in websocket.sent_messages] == [
            "session.update",
            "conversation.item.create",
            "response.create",
            "response.cancel",
            "conversation.item.create",
            "response.create",
        ]
        assert [event.event_type for event in output] == [
            "session_started",
            "final_text",
            "response_completed",
        ]
        assert output[1].text == "new answer"
        assert output[2].usage is not None
        assert output[2].usage.total_tokens == 12

    async def test_realtime_session_manager_ignores_late_terminal_when_next_turn_arrives_after_cancel_error(self):
        websocket = CancelErrorThenDeferredLateDoneWebSocket()
        factory = FakeConnectionFactory(websocket)
        manager = RealtimeSessionManager(
            connection_factory=factory,
            policy=RealtimeSessionPolicy(response_timeout_ms=250),
        )
        config = RealtimeConnectionConfig(
            provider=ProviderId.OPENAI,
            model="gpt-realtime",
            url="wss://example/realtime?model=gpt-realtime",
            headers={"Authorization": "Bearer token"},
        )

        async def events() -> AsyncIterator[RealtimeClientEvent]:
            yield RealtimeClientEvent(event_type="session_start", model="gpt-realtime")
            yield RealtimeClientEvent(event_type="text", model="gpt-realtime", text="hello")
            yield RealtimeClientEvent(event_type="interrupt", model="gpt-realtime")
            await asyncio.wait_for(websocket.error_emitted.wait(), timeout=0.2)
            yield RealtimeClientEvent(event_type="text", model="gpt-realtime", text="again")
            yield RealtimeClientEvent(event_type="close", model="gpt-realtime")

        output = [event async for event in manager.stream(config, events())]

        assert [message["type"] for message in websocket.sent_messages] == [
            "session.update",
            "conversation.item.create",
            "response.create",
            "response.cancel",
            "conversation.item.create",
            "response.create",
        ]
        assert [event.event_type for event in output] == [
            "session_started",
            "final_text",
            "response_completed",
        ]
        assert output[1].text == "fresh answer"
        assert output[2].usage is not None
        assert output[2].usage.total_tokens == 10

    async def test_realtime_session_manager_preserves_deferred_audio_chunk_before_audio_commit_after_interrupt(self):
        websocket = DeferredAudioCommitRaceWebSocket()
        factory = FakeConnectionFactory(websocket)
        manager = RealtimeSessionManager(
            connection_factory=factory,
            policy=RealtimeSessionPolicy(response_timeout_ms=250),
        )
        config = RealtimeConnectionConfig(
            provider=ProviderId.OPENAI,
            model="gpt-realtime",
            url="wss://example/realtime?model=gpt-realtime",
            headers={"Authorization": "Bearer token"},
        )

        async def events() -> AsyncIterator[RealtimeClientEvent]:
            yield RealtimeClientEvent(event_type="session_start", model="gpt-realtime")
            yield RealtimeClientEvent(event_type="text", model="gpt-realtime", text="hello")
            yield RealtimeClientEvent(event_type="interrupt", model="gpt-realtime")
            yield RealtimeClientEvent(event_type="audio_chunk", model="gpt-realtime", audio_chunk=b"again")
            yield RealtimeClientEvent(event_type="audio_commit", model="gpt-realtime")
            yield RealtimeClientEvent(event_type="close", model="gpt-realtime")

        output = [event async for event in manager.stream(config, events())]

        assert [message["type"] for message in websocket.sent_messages] == [
            "session.update",
            "conversation.item.create",
            "response.create",
            "response.cancel",
            "input_audio_buffer.append",
            "input_audio_buffer.commit",
            "response.create",
        ]
        assert [event.event_type for event in output] == [
            "session_started",
            "final_transcript",
            "response_completed",
        ]
        assert output[1].transcript == "again"

    async def test_realtime_session_manager_preserves_followup_audio_after_interrupt_cancel_error(self):
        websocket = CancelErrorThenDeferredLateDoneWebSocket()
        factory = FakeConnectionFactory(websocket)
        manager = RealtimeSessionManager(
            connection_factory=factory,
            policy=RealtimeSessionPolicy(response_timeout_ms=250),
        )
        config = RealtimeConnectionConfig(
            provider=ProviderId.OPENAI,
            model="gpt-realtime",
            url="wss://example/realtime?model=gpt-realtime",
            headers={"Authorization": "Bearer token"},
        )

        async def events() -> AsyncIterator[RealtimeClientEvent]:
            yield RealtimeClientEvent(event_type="session_start", model="gpt-realtime")
            yield RealtimeClientEvent(event_type="text", model="gpt-realtime", text="hello")
            yield RealtimeClientEvent(event_type="interrupt", model="gpt-realtime")
            await asyncio.wait_for(websocket.error_emitted.wait(), timeout=0.2)
            yield RealtimeClientEvent(event_type="audio_chunk", model="gpt-realtime", audio_chunk=b"again")
            yield RealtimeClientEvent(event_type="audio_commit", model="gpt-realtime")
            yield RealtimeClientEvent(event_type="close", model="gpt-realtime")

        output = [event async for event in manager.stream(config, events())]

        assert [message["type"] for message in websocket.sent_messages] == [
            "session.update",
            "conversation.item.create",
            "response.create",
            "response.cancel",
            "input_audio_buffer.append",
            "input_audio_buffer.commit",
            "response.create",
        ]
        assert [event.event_type for event in output] == [
            "session_started",
            "final_text",
            "response_completed",
        ]
        assert output[1].text == "fresh answer"

    async def test_realtime_session_manager_ignores_late_audio_and_terminal_when_next_turn_arrives_after_cancel_error(self):
        websocket = CancelErrorThenDeferredLateAudioWebSocket()
        factory = FakeConnectionFactory(websocket)
        manager = RealtimeSessionManager(
            connection_factory=factory,
            policy=RealtimeSessionPolicy(response_timeout_ms=250),
        )
        config = RealtimeConnectionConfig(
            provider=ProviderId.OPENAI,
            model="gpt-realtime",
            url="wss://example/realtime?model=gpt-realtime",
            headers={"Authorization": "Bearer token"},
        )

        async def events() -> AsyncIterator[RealtimeClientEvent]:
            yield RealtimeClientEvent(event_type="session_start", model="gpt-realtime")
            yield RealtimeClientEvent(event_type="text", model="gpt-realtime", text="hello")
            yield RealtimeClientEvent(event_type="interrupt", model="gpt-realtime")
            await asyncio.wait_for(websocket.error_emitted.wait(), timeout=0.2)
            yield RealtimeClientEvent(event_type="text", model="gpt-realtime", text="again")
            yield RealtimeClientEvent(event_type="close", model="gpt-realtime")

        output = [event async for event in manager.stream(config, events())]

        assert [message["type"] for message in websocket.sent_messages] == [
            "session.update",
            "conversation.item.create",
            "response.create",
            "response.cancel",
            "conversation.item.create",
            "response.create",
        ]
        assert [event.event_type for event in output] == [
            "session_started",
            "final_text",
            "response_completed",
        ]
        assert output[1].text == "fresh answer"
        assert output[2].usage is not None
        assert output[2].usage.total_tokens == 10

    async def test_realtime_session_manager_does_not_send_cancel_after_response_completed(self):
        websocket = CompletedResponseThenCancelErrorWebSocket()
        factory = FakeConnectionFactory(websocket)
        manager = RealtimeSessionManager(
            connection_factory=factory,
            policy=RealtimeSessionPolicy(response_timeout_ms=250),
        )
        config = RealtimeConnectionConfig(
            provider=ProviderId.OPENAI,
            model="gpt-realtime",
            url="wss://example/realtime?model=gpt-realtime",
            headers={"Authorization": "Bearer token"},
        )

        async def events() -> AsyncIterator[RealtimeClientEvent]:
            yield RealtimeClientEvent(event_type="session_start", model="gpt-realtime")
            yield RealtimeClientEvent(event_type="text", model="gpt-realtime", text="hello")
            await asyncio.wait_for(websocket.response_done_emitted.wait(), timeout=0.2)
            await asyncio.sleep(0.01)
            yield RealtimeClientEvent(event_type="interrupt", model="gpt-realtime")
            yield RealtimeClientEvent(event_type="text", model="gpt-realtime", text="again")
            yield RealtimeClientEvent(event_type="close", model="gpt-realtime")

        output = [event async for event in manager.stream(config, events())]

        assert [message["type"] for message in websocket.sent_messages] == [
            "session.update",
            "conversation.item.create",
            "response.create",
            "conversation.item.create",
            "response.create",
        ]
        assert [event.event_type for event in output] == [
            "session_started",
            "response_completed",
            "final_text",
            "response_completed",
        ]
        assert output[2].text == "follow-up answer"
        assert output[3].usage is not None
        assert output[3].usage.total_tokens == 9

    async def test_text_waits_for_session_start_drain_before_response_create(self):
        websocket = GuardedSessionStartWebSocket()
        factory = FakeConnectionFactory(websocket)
        manager = RealtimeSessionManager(connection_factory=factory)
        config = RealtimeConnectionConfig(
            provider=ProviderId.OPENAI,
            model="gpt-4o-mini",
            url="wss://example/realtime?model=gpt-4o-mini",
            headers={"Authorization": "Bearer token"},
        )

        async def events() -> AsyncIterator[RealtimeClientEvent]:
            yield RealtimeClientEvent(
                event_type="session_start",
                provider=ProviderId.OPENAI,
                model="gpt-4o-mini",
                metadata={"session_type": "realtime", "output_audio": "true"},
            )
            yield RealtimeClientEvent(
                event_type="text",
                provider=ProviderId.OPENAI,
                model="gpt-4o-mini",
                text="hello",
            )

        output = [event async for event in manager.stream(config, events())]

        assert [message["type"] for message in websocket.sent_messages] == [
            "session.update",
            "conversation.item.create",
            "response.create",
        ]
        assert [event.event_type for event in output] == ["session_started", "response_completed"]

    async def test_realtime_session_manager_times_out_on_idle_session(self):
        websocket = FakeWebSocket([])
        factory = FakeConnectionFactory(websocket)
        manager = RealtimeSessionManager(
            connection_factory=factory,
            policy=RealtimeSessionPolicy(idle_timeout_ms=5),
        )
        config = RealtimeConnectionConfig(
            provider=ProviderId.OPENAI,
            model="gpt-4o-mini",
            url="wss://example/realtime?model=gpt-4o-mini",
            headers={"Authorization": "Bearer token"},
        )

        async def events() -> AsyncIterator[RealtimeClientEvent]:
            await asyncio.sleep(0.02)
            yield RealtimeClientEvent(event_type="session_start", model="gpt-4o-mini")

        with pytest.raises(GatewayError) as exc:
            _ = [event async for event in manager.stream(config, events())]
        assert "idle timeout" in str(exc.value)

    async def test_openai_realtime_adapter_uses_first_event_model(self):
        websocket = FakeWebSocket([{"type": "session.created"}])
        factory = FakeConnectionFactory(websocket)
        manager = RealtimeSessionManager(connection_factory=factory)
        adapter = OpenAIRealtimeAdapter(
            provider=ProviderId.OPENAI,
            secrets=ProviderConfig(api_key="token"),
            session_manager=manager,
        )

        async def events() -> AsyncIterator[RealtimeClientEvent]:
            yield RealtimeClientEvent(event_type="session_start", model="gpt-4o-mini")

        result = [event async for event in adapter.session(events(), RuntimeProviderConfig())]
        assert result[0].event_type == "session_started"
        assert "model=gpt-4o-mini" in factory.calls[0][0]

    async def test_openai_url_and_headers(self):
        url = build_openai_realtime_url(
            ProviderConfig(api_key="token", base_url="https://api.openai.com/v1"),
            "gpt-4o-mini",
        )
        headers = build_openai_realtime_headers(ProviderConfig(api_key="token"))
        assert url == "wss://api.openai.com/v1/realtime?model=gpt-4o-mini"
        assert headers["OpenAI-Beta"] == "realtime=v1"

    async def test_output_text_delta_maps_to_partial_text(self):
        event = map_openai_event_to_server(
            {"type": "response.output_text.delta", "delta": "he"},
            provider=ProviderId.OPENAI,
            model="gpt-realtime",
        )
        assert event.event_type == "partial_text"
        assert event.text == "he"

    async def test_output_text_done_maps_to_final_text(self):
        event = map_openai_event_to_server(
            {"type": "response.output_text.done", "text": "hello"},
            provider=ProviderId.OPENAI,
            model="gpt-realtime",
        )
        assert event.event_type == "final_text"
        assert event.text == "hello"

    async def test_output_audio_transcript_delta_maps_to_partial_text(self):
        event = map_openai_event_to_server(
            {"type": "response.output_audio_transcript.delta", "delta": "你好"},
            provider=ProviderId.OPENAI,
            model="gpt-realtime",
        )
        assert event.event_type == "partial_text"
        assert event.text == "你好"

    async def test_output_audio_delta_maps_to_audio_chunk(self):
        event = map_openai_event_to_server(
            {
                "type": "response.output_audio.delta",
                "delta": "AQI=",
                "mime_type": "audio/pcm",
                "sequence_number": 3,
            },
            provider=ProviderId.OPENAI,
            model="gpt-realtime",
        )
        assert event.event_type == "audio_chunk"
        assert event.audio_chunk == b"\x01\x02"
        assert event.mime_type == "audio/pcm"
        assert event.sequence == 3

    async def test_response_done_cancelled_maps_to_cancelled_event(self):
        event = map_openai_event_to_server(
            {"type": "response.done", "response": {"status": "cancelled"}},
            provider=ProviderId.OPENAI,
            model="gpt-4o-mini",
        )
        assert event.event_type == "cancelled"
