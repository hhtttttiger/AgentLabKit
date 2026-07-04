from __future__ import annotations

import json
from collections.abc import AsyncIterator

import pytest

from llm_gateway.core.adapters import SpeechBatchAdapter
from llm_gateway.core.speech_stream import BufferedSpeechStreamAdapter
from llm_gateway.config import ProviderConfig
from llm_gateway.models import (
    ProviderId,
    SpeechStreamChunk,
    SpeechTranscribeResponse,
    UsageInfo,
)
from llm_gateway.provider_runtime import RuntimeProviderConfig
from llm_gateway.providers.openai.realtime import RealtimeSessionManager
from llm_gateway.providers.openai.speech import OpenAISpeechStreamAdapter


class FakeSpeechBatchAdapter(SpeechBatchAdapter):
    def __init__(self) -> None:
        self.requests = []

    async def transcribe(self, request, runtime_config: RuntimeProviderConfig):
        del runtime_config
        self.requests.append(request)
        return SpeechTranscribeResponse(
            provider=ProviderId.OPENAI,
            model=request.model,
            transcript=request.audio.decode("utf-8"),
            usage=UsageInfo(audio_duration_ms=100),
        )


async def _async_chunks(items) -> AsyncIterator[SpeechStreamChunk]:
    for item in items:
        yield item


class FakeWebSocket:
    def __init__(self, incoming_messages: list[dict]) -> None:
        self.incoming_messages = [json.dumps(item) for item in incoming_messages]
        self.sent_messages: list[dict] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def send(self, payload: str) -> None:
        self.sent_messages.append(json.loads(payload))

    async def recv(self) -> str:
        return self.incoming_messages.pop(0)

    async def close(self) -> None:
        return None


class FakeConnectionFactory:
    def __init__(self, websocket: FakeWebSocket) -> None:
        self.websocket = websocket
        self.calls: list[tuple[str, dict[str, str]]] = []

    def __call__(self, url: str, additional_headers: dict[str, str], **kwargs):
        self.calls.append((url, additional_headers))
        return self.websocket


@pytest.mark.asyncio
class TestBufferedSpeechStreamAdapter:
    async def test_buffers_chunks_until_end_of_audio(self):
        batch_adapter = FakeSpeechBatchAdapter()
        adapter = BufferedSpeechStreamAdapter(batch_adapter, provider=ProviderId.OPENAI)
        chunks = _async_chunks(
            [
                SpeechStreamChunk(
                    provider=ProviderId.OPENAI,
                    model="gpt-4o-mini-transcribe",
                    audio_chunk=b"he",
                    mime_type="audio/wav",
                    end_of_audio=False,
                ),
                SpeechStreamChunk(
                    provider=ProviderId.OPENAI,
                    model="gpt-4o-mini-transcribe",
                    audio_chunk=b"llo",
                    mime_type="audio/wav",
                    end_of_audio=True,
                ),
            ]
        )
        events = [event async for event in adapter.transcribe_stream(chunks, RuntimeProviderConfig())]
        assert batch_adapter.requests[0].audio == b"hello"
        assert events[0].transcript == "hello"
        assert events[0].is_final

    async def test_empty_stream_returns_no_events(self):
        batch_adapter = FakeSpeechBatchAdapter()
        adapter = BufferedSpeechStreamAdapter(batch_adapter, provider=ProviderId.OPENAI)
        events = [event async for event in adapter.transcribe_stream(_async_chunks([]), RuntimeProviderConfig())]
        assert events == []


@pytest.mark.asyncio
class TestOpenAISpeechStreamAdapter:
    async def test_emits_partial_and_final_transcripts(self):
        websocket = FakeWebSocket(
            [
                {"type": "session.created"},
                {"type": "conversation.item.input_audio_transcription.delta", "delta": "hel"},
                {"type": "conversation.item.input_audio_transcription.completed", "transcript": "hello"},
                {
                    "type": "response.done",
                    "response": {
                        "status": "completed",
                        "usage": {"input_tokens": 9, "output_tokens": 4},
                    },
                },
            ]
        )
        adapter = OpenAISpeechStreamAdapter(
            ProviderConfig(api_key="token"),
            session_manager=RealtimeSessionManager(
                connection_factory=FakeConnectionFactory(websocket)
            ),
        )
        chunks = _async_chunks(
            [
                SpeechStreamChunk(
                    provider=ProviderId.OPENAI,
                    model="gpt-4o-mini-transcribe",
                    audio_chunk=b"he",
                    mime_type="audio/wav",
                    end_of_audio=False,
                ),
                SpeechStreamChunk(
                    provider=ProviderId.OPENAI,
                    model="gpt-4o-mini-transcribe",
                    audio_chunk=b"llo",
                    mime_type="audio/wav",
                    end_of_audio=True,
                ),
            ]
        )
        events = [event async for event in adapter.transcribe_stream(chunks, RuntimeProviderConfig())]
        assert [event.event_type for event in events] == ["partial_transcript", "final_transcript"]
        assert events[-1].transcript == "hello"
        assert events[-1].usage is not None
        assert events[-1].usage.input_tokens == 9
        assert events[-1].usage.output_tokens == 4
        assert events[-1].usage.total_tokens == 13
        assert websocket.sent_messages[0]["type"] == "session.update"
        assert websocket.sent_messages[0]["session"]["type"] == "transcription"
        assert websocket.sent_messages[0]["session"]["input_audio_transcription"] == {
            "model": "gpt-4o-mini-transcribe"
        }
        assert websocket.sent_messages[0]["session"]["input_audio_format"] == "audio/wav"
        assert "input_audio_buffer.commit" in [
            message["type"] for message in websocket.sent_messages
        ]
        assert "response.create" not in [
            message["type"] for message in websocket.sent_messages
        ]
