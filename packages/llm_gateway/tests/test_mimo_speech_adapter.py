"""Tests for speech-to-text adapters.

Covers:
- Chat-completions-based adapters (``/v1/chat/completions`` with ``input_audio``)
- HTTP SSE streaming adapter (``/audio/transcriptions`` with ``stream=True``)
- Composite routing adapters
"""

from __future__ import annotations

import base64
from collections.abc import AsyncIterator
from types import SimpleNamespace

import pytest

from llm_gateway.config import ProviderConfig
from llm_gateway.models import (
    ProviderId,
    SpeechStreamChunk,
    SpeechTranscribeRequest,
    UsageInfo,
)
from llm_gateway.provider_runtime import RuntimeProviderConfig
from llm_gateway.providers.openai.chat_speech import (
    OpenAIChatSpeechBatchAdapter,
    OpenAIChatSpeechStreamAdapter,
    _build_audio_content,
    _extract_asr_options,
    _map_usage,
)
from llm_gateway.providers.openai.speech import OpenAITranscriptionStreamAdapter
from llm_gateway.providers.openai.speech_router import (
    CompositeSpeechBatchAdapter,
    CompositeSpeechStreamAdapter,
)
from llm_gateway.core.adapters import SpeechBatchAdapter, SpeechStreamAdapter


# ── Helpers ──────────────────────────────────────────────────────────────────


def _audio_bytes(text: str = "hello") -> bytes:
    return text.encode("utf-8")


def _b64(text: str = "hello") -> str:
    return base64.b64encode(_audio_bytes(text)).decode("ascii")


# ── Fake OpenAI SDK objects ──────────────────────────────────────────────────


class FakeUsage:
    def __init__(
        self,
        prompt_tokens: int = 10,
        completion_tokens: int = 5,
        total_tokens: int = 15,
        audio_tokens: int | None = 8,
        seconds: float | None = 2.5,
    ):
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.total_tokens = total_tokens
        self.prompt_tokens_details = (
            SimpleNamespace(audio_tokens=audio_tokens) if audio_tokens is not None else None
        )
        self.seconds = seconds


class FakeMessage:
    def __init__(self, content: str):
        self.content = content
        self.role = "assistant"


class FakeChoice:
    def __init__(self, content: str, finish_reason: str | None = None):
        self.message = FakeMessage(content)
        self.finish_reason = finish_reason
        self.index = 0


class FakeCompletionResult:
    def __init__(self, text: str = "transcribed text", usage: FakeUsage | None = None):
        self.choices = [FakeChoice(text)]
        self.usage = usage or FakeUsage()
        self.id = "chatcmpl-123"
        self.model = "mimo-v2.5-asr"


class FakeStreamDelta:
    def __init__(self, content: str | None):
        self.content = content
        self.role = None


class FakeStreamChoice:
    def __init__(self, content: str | None, finish_reason: str | None = None):
        self.delta = FakeStreamDelta(content)
        self.finish_reason = finish_reason
        self.index = 0


class FakeStreamChunk:
    def __init__(
        self,
        content: str | None = None,
        finish_reason: str | None = None,
        usage: FakeUsage | None = None,
    ):
        self.choices = [FakeStreamChoice(content, finish_reason)] if content is not None or finish_reason else []
        self.usage = usage
        self.id = "chatcmpl-123"
        self.model = "mimo-v2.5-asr"


class FakeStream:
    def __init__(self, chunks: list[FakeStreamChunk]):
        self._chunks = chunks

    def __aiter__(self):
        return self._aiter()

    async def _aiter(self):
        for chunk in self._chunks:
            yield chunk


class FakeChatCompletions:
    def __init__(
        self,
        result: FakeCompletionResult | None = None,
        stream_chunks: list[FakeStreamChunk] | None = None,
    ):
        self._result = result or FakeCompletionResult()
        self._stream_chunks = stream_chunks
        self.calls: list[dict] = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        if kwargs.get("stream"):
            return FakeStream(self._stream_chunks or [
                FakeStreamChunk("partial "),
                FakeStreamChunk("text"),
                FakeStreamChunk(finish_reason="stop", usage=FakeUsage()),
            ])
        return self._result


class FakeClient:
    def __init__(self, **kwargs):
        self.chat = SimpleNamespace(completions=FakeChatCompletions(**kwargs))


# ── Unit tests for helper functions ─────────────────────────────────────────


class TestBuildAudioContent:
    def test_builds_data_url_with_wav(self):
        result = _build_audio_content(b"\x00\x01", "audio/wav")
        assert result["type"] == "input_audio"
        data = result["input_audio"]["data"]
        assert data.startswith("data:audio/wav;base64,")

    def test_builds_data_url_with_mp3(self):
        result = _build_audio_content(b"\xff\xfb", "audio/mpeg")
        assert result["input_audio"]["data"].startswith("data:audio/mpeg;base64,")

    def test_base64_encoding_is_correct(self):
        audio = b"test audio"
        result = _build_audio_content(audio, "audio/wav")
        data_url = result["input_audio"]["data"]
        b64_part = data_url.split(",", 1)[1]
        decoded = base64.b64decode(b64_part)
        assert decoded == audio


class TestExtractAsrOptions:
    def test_returns_language_when_present(self):
        result = _extract_asr_options({"asr_language": "zh"})
        assert result == {"language": "zh"}

    def test_returns_none_when_absent(self):
        result = _extract_asr_options({})
        assert result is None

    def test_returns_none_for_other_metadata(self):
        result = _extract_asr_options({"foo": "bar"})
        assert result is None


class TestMapUsage:
    def test_maps_full_usage(self):
        usage = FakeUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15, audio_tokens=8, seconds=2.5)
        result = _map_usage(SimpleNamespace(usage=usage))
        assert result is not None
        assert result.input_tokens == 10
        assert result.output_tokens == 5
        assert result.total_tokens == 15
        assert result.audio_duration_ms == 2500

    def test_returns_none_when_no_usage(self):
        result = _map_usage(SimpleNamespace(usage=None))
        assert result is None

    def test_handles_missing_seconds(self):
        usage = SimpleNamespace(
            prompt_tokens=1, completion_tokens=2, total_tokens=3,
            prompt_tokens_details=None, seconds=None,
        )
        result = _map_usage(SimpleNamespace(usage=usage))
        assert result is not None
        assert result.audio_duration_ms is None


# ── OpenAIChatSpeechBatchAdapter ─────────────────────────────────────────────


@pytest.mark.asyncio
class TestOpenAIChatSpeechBatchAdapter:
    async def test_transcribe_basic(self):
        client = FakeClient(result=FakeCompletionResult("hello world"))
        adapter = OpenAIChatSpeechBatchAdapter(
            ProviderConfig(api_key="test-key"),
            client=client,
        )
        response = await adapter.transcribe(
            SpeechTranscribeRequest(
                model="mimo-v2.5-asr",
                audio=_audio_bytes("hello"),
                mime_type="audio/wav",
            ),
            RuntimeProviderConfig(),
        )
        assert response.transcript == "hello world"
        assert response.provider == ProviderId.OPENAI
        assert response.model == "mimo-v2.5-asr"
        assert response.usage is not None
        assert response.usage.input_tokens == 10

    async def test_transcribe_passes_asr_language(self):
        client = FakeClient()
        adapter = OpenAIChatSpeechBatchAdapter(
            ProviderConfig(api_key="test-key"),
            client=client,
        )
        await adapter.transcribe(
            SpeechTranscribeRequest(
                model="mimo-v2.5-asr",
                audio=_audio_bytes(),
                mime_type="audio/wav",
                metadata={"asr_language": "zh"},
            ),
            RuntimeProviderConfig(),
        )
        call = client.chat.completions.calls[0]
        assert call["extra_body"] == {"asr_options": {"language": "zh"}}

    async def test_transcribe_no_extra_body_when_no_options(self):
        client = FakeClient()
        adapter = OpenAIChatSpeechBatchAdapter(
            ProviderConfig(api_key="test-key"),
            client=client,
        )
        await adapter.transcribe(
            SpeechTranscribeRequest(
                model="mimo-v2.5-asr",
                audio=_audio_bytes(),
                mime_type="audio/wav",
            ),
            RuntimeProviderConfig(),
        )
        call = client.chat.completions.calls[0]
        assert "extra_body" not in call

    async def test_transcribe_sends_correct_message_format(self):
        client = FakeClient()
        adapter = OpenAIChatSpeechBatchAdapter(
            ProviderConfig(api_key="test-key"),
            client=client,
        )
        await adapter.transcribe(
            SpeechTranscribeRequest(
                model="mimo-v2.5-asr",
                audio=_audio_bytes("test"),
                mime_type="audio/mp3",
            ),
            RuntimeProviderConfig(),
        )
        call = client.chat.completions.calls[0]
        assert call["model"] == "mimo-v2.5-asr"
        messages = call["messages"]
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        content = messages[0]["content"]
        assert len(content) == 1
        assert content[0]["type"] == "input_audio"
        assert content[0]["input_audio"]["data"].startswith("data:audio/mp3;base64,")

    async def test_transcribe_maps_audio_duration(self):
        usage = FakeUsage(seconds=3.0)
        client = FakeClient(result=FakeCompletionResult("result", usage=usage))
        adapter = OpenAIChatSpeechBatchAdapter(
            ProviderConfig(api_key="test-key"),
            client=client,
        )
        response = await adapter.transcribe(
            SpeechTranscribeRequest(
                model="mimo-v2.5-asr",
                audio=_audio_bytes(),
                mime_type="audio/wav",
            ),
            RuntimeProviderConfig(),
        )
        assert response.usage is not None
        assert response.usage.audio_duration_ms == 3000

    async def test_transcribe_empty_choices(self):
        result = FakeCompletionResult("ignored")
        result.choices = []
        client = FakeClient(result=result)
        adapter = OpenAIChatSpeechBatchAdapter(
            ProviderConfig(api_key="test-key"),
            client=client,
        )
        response = await adapter.transcribe(
            SpeechTranscribeRequest(
                model="mimo-v2.5-asr",
                audio=_audio_bytes(),
                mime_type="audio/wav",
            ),
            RuntimeProviderConfig(),
        )
        assert response.transcript == ""

    async def test_transcribe_uses_runtime_config(self):
        client = FakeClient()
        adapter = OpenAIChatSpeechBatchAdapter(
            ProviderConfig(api_key="test-key"),
            client=client,
        )
        # Same credentials — uses cached client. Verifies the adapter
        # accepts runtime_config without errors.
        response = await adapter.transcribe(
            SpeechTranscribeRequest(
                model="mimo-v2.5-asr",
                audio=_audio_bytes(),
                mime_type="audio/wav",
            ),
            RuntimeProviderConfig(api_key="test-key"),
        )
        assert response.transcript == "transcribed text"


# ── OpenAIChatSpeechStreamAdapter ────────────────────────────────────────────


@pytest.mark.asyncio
class TestOpenAIChatSpeechStreamAdapter:
    async def test_stream_basic(self):
        chunks = [
            FakeStreamChunk("hello "),
            FakeStreamChunk("world"),
            FakeStreamChunk(finish_reason="stop", usage=FakeUsage(seconds=1.5)),
        ]
        client = FakeClient(stream_chunks=chunks)
        adapter = OpenAIChatSpeechStreamAdapter(
            ProviderConfig(api_key="test-key"),
            client=client,
        )

        audio_chunks = _async_chunks([
            SpeechStreamChunk(
                provider=ProviderId.OPENAI,
                model="mimo-v2.5-asr",
                audio_chunk=b"hello ",
                mime_type="audio/wav",
            ),
            SpeechStreamChunk(
                provider=ProviderId.OPENAI,
                model="mimo-v2.5-asr",
                audio_chunk=b"world",
                mime_type="audio/wav",
                end_of_audio=True,
            ),
        ])

        events = [event async for event in adapter.transcribe_stream(audio_chunks, RuntimeProviderConfig())]

        assert len(events) == 3
        assert events[0].event_type == "partial_transcript"
        assert events[0].transcript == "hello "
        assert events[0].is_final is False

        assert events[1].event_type == "partial_transcript"
        assert events[1].transcript == "world"

        assert events[2].event_type == "final_transcript"
        assert events[2].transcript == "hello world"
        assert events[2].is_final is True
        assert events[2].usage is not None
        assert events[2].usage.audio_duration_ms == 1500

    async def test_stream_passes_asr_options(self):
        chunks = [FakeStreamChunk("text", finish_reason="stop", usage=FakeUsage())]
        client = FakeClient(stream_chunks=chunks)
        adapter = OpenAIChatSpeechStreamAdapter(
            ProviderConfig(api_key="test-key"),
            client=client,
        )

        audio_chunks = _async_chunks([
            SpeechStreamChunk(
                provider=ProviderId.OPENAI,
                model="mimo-v2.5-asr",
                audio_chunk=b"audio",
                mime_type="audio/wav",
                end_of_audio=True,
                metadata={"asr_language": "en"},
            ),
        ])

        events = [event async for event in adapter.transcribe_stream(audio_chunks, RuntimeProviderConfig())]
        call = client.chat.completions.calls[0]
        assert call["extra_body"] == {"asr_options": {"language": "en"}}
        assert call["stream"] is True

    async def test_stream_empty_input(self):
        client = FakeClient()
        adapter = OpenAIChatSpeechStreamAdapter(
            ProviderConfig(api_key="test-key"),
            client=client,
        )
        events = [event async for event in adapter.transcribe_stream(_async_chunks([]), RuntimeProviderConfig())]
        assert events == []

    async def test_stream_no_content_deltas_skipped(self):
        chunks = [
            FakeStreamChunk(None),  # role-only chunk
            FakeStreamChunk("text"),
            FakeStreamChunk(finish_reason="stop", usage=FakeUsage()),
        ]
        client = FakeClient(stream_chunks=chunks)
        adapter = OpenAIChatSpeechStreamAdapter(
            ProviderConfig(api_key="test-key"),
            client=client,
        )

        audio_chunks = _async_chunks([
            SpeechStreamChunk(
                provider=ProviderId.OPENAI,
                model="mimo-v2.5-asr",
                audio_chunk=b"audio",
                mime_type="audio/wav",
                end_of_audio=True,
            ),
        ])

        events = [event async for event in adapter.transcribe_stream(audio_chunks, RuntimeProviderConfig())]
        # Chunk 1 (content=None, no finish) → skipped.
        # Chunk 2 (content="text") → partial_transcript.
        # Chunk 3 (finish_reason="stop", no content) → final_transcript.
        assert len(events) == 2
        assert events[0].event_type == "partial_transcript"
        assert events[0].transcript == "text"
        assert events[0].is_final is False
        assert events[1].event_type == "final_transcript"
        assert events[1].transcript == "text"
        assert events[1].is_final is True


# ── Composite adapters ──────────────────────────────────────────────────────


class RecordingBatchAdapter(SpeechBatchAdapter):
    def __init__(self, name: str):
        self.name = name
        self.calls: list[str] = []

    async def transcribe(self, request, runtime_config):
        self.calls.append(request.model)
        from llm_gateway.models import SpeechTranscribeResponse
        return SpeechTranscribeResponse(
            provider=ProviderId.OPENAI,
            model=request.model,
            transcript=f"{self.name}:{request.model}",
        )


class RecordingStreamAdapter(SpeechStreamAdapter):
    def __init__(self, name: str):
        self.name = name
        self.calls: list[str] = []

    async def transcribe_stream(self, chunks, runtime_config):
        async for chunk in chunks:
            self.calls.append(chunk.model)
            from llm_gateway.models import SpeechStreamEvent
            yield SpeechStreamEvent(
                event_type="final_transcript",
                provider=ProviderId.OPENAI,
                model=chunk.model,
                transcript=f"{self.name}:{chunk.model}",
                is_final=True,
            )
            break


async def _async_chunks(items) -> AsyncIterator:
    for item in items:
        yield item


@pytest.mark.asyncio
class TestCompositeSpeechBatchAdapter:
    async def test_routes_to_chat_adapter_for_mimo(self):
        default = RecordingBatchAdapter("default")
        chat = RecordingBatchAdapter("chat")
        composite = CompositeSpeechBatchAdapter(
            default=default, chat=chat, chat_models={"mimo-v2.5-asr"},
        )
        response = await composite.transcribe(
            SpeechTranscribeRequest(model="mimo-v2.5-asr", audio=b"a", mime_type="audio/wav"),
            RuntimeProviderConfig(),
        )
        assert response.transcript == "chat:mimo-v2.5-asr"
        assert chat.calls == ["mimo-v2.5-asr"]
        assert default.calls == []

    async def test_routes_to_default_adapter_for_openai(self):
        default = RecordingBatchAdapter("default")
        chat = RecordingBatchAdapter("chat")
        composite = CompositeSpeechBatchAdapter(
            default=default, chat=chat, chat_models={"mimo-v2.5-asr"},
        )
        response = await composite.transcribe(
            SpeechTranscribeRequest(model="gpt-4o-mini-transcribe", audio=b"a", mime_type="audio/wav"),
            RuntimeProviderConfig(),
        )
        assert response.transcript == "default:gpt-4o-mini-transcribe"
        assert default.calls == ["gpt-4o-mini-transcribe"]
        assert chat.calls == []


@pytest.mark.asyncio
class TestCompositeSpeechStreamAdapter:
    async def test_routes_to_chat_adapter_for_mimo(self):
        default = RecordingStreamAdapter("default")
        chat = RecordingStreamAdapter("chat")
        composite = CompositeSpeechStreamAdapter(
            default=default, chat=chat, chat_models={"mimo-v2.5-asr"},
        )
        audio_chunks = _async_chunks([
            SpeechStreamChunk(
                provider=ProviderId.OPENAI,
                model="mimo-v2.5-asr",
                audio_chunk=b"audio",
                mime_type="audio/wav",
                end_of_audio=True,
            ),
        ])
        events = [event async for event in composite.transcribe_stream(audio_chunks, RuntimeProviderConfig())]
        assert events[0].transcript == "chat:mimo-v2.5-asr"
        assert chat.calls == ["mimo-v2.5-asr"]
        assert default.calls == []

    async def test_routes_to_default_adapter_for_openai(self):
        default = RecordingStreamAdapter("default")
        chat = RecordingStreamAdapter("chat")
        composite = CompositeSpeechStreamAdapter(
            default=default, chat=chat, chat_models={"mimo-v2.5-asr"},
        )
        audio_chunks = _async_chunks([
            SpeechStreamChunk(
                provider=ProviderId.OPENAI,
                model="gpt-4o-mini-transcribe",
                audio_chunk=b"audio",
                mime_type="audio/wav",
                end_of_audio=True,
            ),
        ])
        events = [event async for event in composite.transcribe_stream(audio_chunks, RuntimeProviderConfig())]
        assert events[0].transcript == "default:gpt-4o-mini-transcribe"
        assert default.calls == ["gpt-4o-mini-transcribe"]
        assert chat.calls == []

    async def test_empty_stream_returns_no_events(self):
        default = RecordingStreamAdapter("default")
        chat = RecordingStreamAdapter("chat")
        composite = CompositeSpeechStreamAdapter(
            default=default, chat=chat, chat_models={"mimo-v2.5-asr"},
        )
        events = [event async for event in composite.transcribe_stream(_async_chunks([]), RuntimeProviderConfig())]
        assert events == []


# ── OpenAI /audio/transcriptions SSE streaming ───────────────────────────────


class FakeTranscriptionDeltaEvent:
    """Mimics ``transcript.text.delta`` SSE event from OpenAI transcription API."""

    def __init__(self, delta: str):
        self.type = "transcript.text.delta"
        self.delta = delta


class FakeTranscriptionDoneEvent:
    """Mimics ``transcript.text.done`` SSE event from OpenAI transcription API."""

    def __init__(self, text: str, seconds: float | None = None):
        self.type = "transcript.text.done"
        self.text = text
        if seconds is not None:
            self.usage = SimpleNamespace(type="duration", seconds=seconds)
        else:
            self.usage = None


class FakeTranscriptionStream:
    def __init__(self, events: list):
        self._events = events

    def __aiter__(self):
        return self._aiter()

    async def _aiter(self):
        for event in self._events:
            yield event


class FakeTranscriptionCreate:
    def __init__(self, events: list):
        self._events = events
        self.calls: list[dict] = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        if kwargs.get("stream"):
            return FakeTranscriptionStream(self._events)
        return SimpleNamespace(text="not used", usage=None)


class FakeAudioTranscriptions:
    def __init__(self, events: list):
        self.transcriptions = FakeTranscriptionCreate(events)


class FakeTranscriptionClient:
    def __init__(self, events: list):
        self.audio = FakeAudioTranscriptions(events)


@pytest.mark.asyncio
class TestOpenAITranscriptionStreamAdapter:
    async def test_streams_partial_and_final_transcripts(self):
        events = [
            FakeTranscriptionDeltaEvent("hel"),
            FakeTranscriptionDeltaEvent("lo world"),
            FakeTranscriptionDoneEvent("hello world", seconds=2.5),
        ]
        client = FakeTranscriptionClient(events)
        adapter = OpenAITranscriptionStreamAdapter(
            ProviderConfig(api_key="test-key"),
            client=client,
        )

        audio_chunks = _async_chunks([
            SpeechStreamChunk(
                provider=ProviderId.OPENAI,
                model="gpt-4o-transcribe",
                audio_chunk=b"RIFF",
                mime_type="audio/wav",
            ),
            SpeechStreamChunk(
                provider=ProviderId.OPENAI,
                model="gpt-4o-transcribe",
                audio_chunk=b"\x00" * 100,
                mime_type="audio/wav",
                end_of_audio=True,
            ),
        ])

        result = [event async for event in adapter.transcribe_stream(audio_chunks, RuntimeProviderConfig())]

        assert len(result) == 3
        assert result[0].event_type == "partial_transcript"
        assert result[0].transcript == "hel"
        assert result[0].is_final is False

        assert result[1].event_type == "partial_transcript"
        assert result[1].transcript == "lo world"

        assert result[2].event_type == "final_transcript"
        assert result[2].transcript == "hello world"
        assert result[2].is_final is True
        assert result[2].usage is not None
        assert result[2].usage.audio_duration_ms == 2500

    async def test_passes_model_and_language_to_api(self):
        events = [FakeTranscriptionDoneEvent("text")]
        client = FakeTranscriptionClient(events)
        adapter = OpenAITranscriptionStreamAdapter(
            ProviderConfig(api_key="test-key"),
            client=client,
        )

        audio_chunks = _async_chunks([
            SpeechStreamChunk(
                provider=ProviderId.OPENAI,
                model="gpt-4o-mini-transcribe",
                audio_chunk=b"audio",
                mime_type="audio/mp3",
                language="zh",
                end_of_audio=True,
            ),
        ])

        async for _ in adapter.transcribe_stream(audio_chunks, RuntimeProviderConfig()):
            pass

        call = client.audio.transcriptions.calls[0]
        assert call["model"] == "gpt-4o-mini-transcribe"
        assert call["language"] == "zh"
        assert call["stream"] is True

    async def test_empty_stream_returns_no_events(self):
        client = FakeTranscriptionClient([])
        adapter = OpenAITranscriptionStreamAdapter(
            ProviderConfig(api_key="test-key"),
            client=client,
        )
        result = [event async for event in adapter.transcribe_stream(_async_chunks([]), RuntimeProviderConfig())]
        assert result == []

    async def test_final_event_without_usage(self):
        events = [
            FakeTranscriptionDeltaEvent("text"),
            FakeTranscriptionDoneEvent("text"),  # no usage
        ]
        client = FakeTranscriptionClient(events)
        adapter = OpenAITranscriptionStreamAdapter(
            ProviderConfig(api_key="test-key"),
            client=client,
        )

        audio_chunks = _async_chunks([
            SpeechStreamChunk(
                provider=ProviderId.OPENAI,
                model="gpt-4o-transcribe",
                audio_chunk=b"audio",
                mime_type="audio/wav",
                end_of_audio=True,
            ),
        ])

        result = [event async for event in adapter.transcribe_stream(audio_chunks, RuntimeProviderConfig())]
        assert result[-1].event_type == "final_transcript"
        assert result[-1].usage is None

    async def test_maps_token_based_usage(self):
        done_event = FakeTranscriptionDoneEvent("text")
        # Override usage with token-based format.
        done_event.usage = SimpleNamespace(
            type="tokens",
            input_tokens=10,
            output_tokens=5,
            total_tokens=15,
            input_token_details=SimpleNamespace(audio_tokens=8),
        )
        events = [done_event]
        client = FakeTranscriptionClient(events)
        adapter = OpenAITranscriptionStreamAdapter(
            ProviderConfig(api_key="test-key"),
            client=client,
        )

        audio_chunks = _async_chunks([
            SpeechStreamChunk(
                provider=ProviderId.OPENAI,
                model="gpt-4o-transcribe",
                audio_chunk=b"audio",
                mime_type="audio/wav",
                end_of_audio=True,
            ),
        ])

        result = [event async for event in adapter.transcribe_stream(audio_chunks, RuntimeProviderConfig())]
        assert result[-1].usage is not None
        assert result[-1].usage.input_tokens == 10
        assert result[-1].usage.total_tokens == 15
