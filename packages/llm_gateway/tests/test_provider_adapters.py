from __future__ import annotations

import wave

from collections.abc import AsyncIterator
from types import SimpleNamespace

import pytest

from llm_gateway.config import ProviderConfig
from llm_gateway.models import (
    EmbeddingGenerateRequest,
    ImageGenerateRequest,
    ProviderId,
    SpeechTranscribeRequest,
    TextGenerateRequest,
)
from llm_gateway.provider_runtime import RuntimeProviderConfig
from llm_gateway.providers.openai.embedding import OpenAIEmbeddingAdapter
from llm_gateway.providers.openai.image import OpenAIImageAdapter
from llm_gateway.providers.openai.speech import OpenAISpeechBatchAdapter
from llm_gateway.providers.openai.text import OpenAITextAdapter


# ---------------------------------------------------------------------------
# OpenAI SDK shaped fakes
# ---------------------------------------------------------------------------

class FakeFinishReason:
    value = "stop"


class FakeMessage:
    def __init__(self, content: str) -> None:
        self.content = content


class FakeChoice:
    def __init__(self, content: str, finish_reason: FakeFinishReason | None = None) -> None:
        self.message = FakeMessage(content)
        self.delta = SimpleNamespace(content=None)
        self.finish_reason = finish_reason or FakeFinishReason()


class FakeCompletionResult:
    def __init__(self, text: str) -> None:
        self.choices = [FakeChoice(text)]
        self.usage = SimpleNamespace(prompt_tokens=1, completion_tokens=2, total_tokens=3)


class FakeStreamChunk:
    def __init__(self, delta_text: str | None = None, *, is_usage: bool = False) -> None:
        self.choices = [SimpleNamespace(delta=SimpleNamespace(content=delta_text))]
        self.usage = SimpleNamespace(prompt_tokens=1, completion_tokens=2, total_tokens=3) if is_usage else None


class FakeStream:
    def __init__(self, chunks: list[FakeStreamChunk]) -> None:
        self._chunks = chunks

    async def __aiter__(self) -> AsyncIterator[FakeStreamChunk]:
        for chunk in self._chunks:
            yield chunk


class FakeChatCompletions:
    def __init__(self, result: FakeCompletionResult | None = None, stream_chunks: list[FakeStreamChunk] | None = None) -> None:
        self._result = result or FakeCompletionResult("text:default")
        self._stream_chunks = stream_chunks
        self.calls: list[dict[str, object]] = []

    async def create(self, **kwargs) -> object:
        self.calls.append(kwargs)
        if kwargs.get("stream"):
            chunks = self._stream_chunks or [
                FakeStreamChunk("he"),
                FakeStreamChunk("llo"),
                FakeStreamChunk(is_usage=True),
            ]
            return FakeStream(chunks)
        return self._result


class FakeTranscriptions:
    async def create(self, **kwargs):
        del kwargs
        return SimpleNamespace(
            text="spoken",
            duration=1.25,
            usage=SimpleNamespace(prompt_tokens=0, completion_tokens=0, total_tokens=0),
        )


class FakeAudio:
    def __init__(self) -> None:
        self.transcriptions = FakeTranscriptions()


class FakeImages:
    async def generate(self, **kwargs):
        del kwargs
        return SimpleNamespace(
            data=[SimpleNamespace(url="https://image.example/generated.png")],
            usage=SimpleNamespace(input_tokens=4, output_tokens=0, total_tokens=4, cost=0.12),
        )


class FakeEmbeddings:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            data=[SimpleNamespace(embedding=[0.01, 0.02, 0.03])],
            usage=SimpleNamespace(prompt_tokens=7, total_tokens=7),
        )


class FakeOpenAIClient:
    def __init__(
        self,
        *,
        chat_result: FakeCompletionResult | None = None,
        stream_chunks: list[FakeStreamChunk] | None = None,
    ) -> None:
        self.audio = FakeAudio()
        self.images = FakeImages()
        self.embeddings = FakeEmbeddings()
        self.chat = SimpleNamespace(
            completions=FakeChatCompletions(result=chat_result, stream_chunks=stream_chunks)
        )


@pytest.mark.asyncio
class TestProviderAdapter:
    async def test_openai_embedding_adapter_maps_usage_and_dimensions(self):
        client = FakeOpenAIClient()
        adapter = OpenAIEmbeddingAdapter(
            ProviderConfig(api_key="token"),
            client=client,
        )
        response = await adapter.generate(
            EmbeddingGenerateRequest(model="text-embedding-3-small", input="abc"),
            RuntimeProviderConfig(),
        )
        assert response.provider == ProviderId.OPENAI
        assert response.embedding == [0.01, 0.02, 0.03]
        assert response.dimensions == 3
        assert response.usage is not None
        assert response.usage.input_tokens == 7
        assert response.usage.total_tokens == 7
        assert client.embeddings.calls[0]["model"] == "text-embedding-3-small"
        assert client.embeddings.calls[0]["input"] == "abc"

    async def test_openai_text_adapter_generate(self):
        client = FakeOpenAIClient(chat_result=FakeCompletionResult("text:hello"))
        adapter = OpenAITextAdapter(
            ProviderConfig(api_key="token"),
            client=client,
        )
        response = await adapter.generate(
            TextGenerateRequest(model="gpt", prompt="hello"),
            RuntimeProviderConfig(),
        )
        assert response.text == "text:hello"
        assert response.usage is not None
        assert response.usage.total_tokens == 3
        assert client.chat.completions.calls[0]["model"] == "gpt"

    async def test_openai_text_adapter_generate_stream(self):
        chunks = [
            FakeStreamChunk("he"),
            FakeStreamChunk("llo"),
            FakeStreamChunk(is_usage=True),
        ]
        client = FakeOpenAIClient(stream_chunks=chunks)
        adapter = OpenAITextAdapter(
            ProviderConfig(api_key="token"),
            client=client,
        )
        events = [
            event
            async for event in adapter.generate_stream(
                TextGenerateRequest(model="gpt", prompt="hello"),
                RuntimeProviderConfig(),
            )
        ]
        assert events[0].delta == "he"
        assert events[1].delta == "llo"
        assert events[-1].text == "hello"
        assert events[-1].usage is not None
        assert events[-1].usage.input_tokens == 1
        assert events[-1].usage.output_tokens == 2
        assert events[-1].usage.total_tokens == 3

    async def test_openai_speech_batch_adapter(self):
        adapter = OpenAISpeechBatchAdapter(
            ProviderConfig(api_key="token"),
            client=FakeOpenAIClient(),
        )
        response = await adapter.transcribe(
            SpeechTranscribeRequest(
                model="gpt-4o-mini-transcribe",
                audio=b"abc",
                mime_type="audio/wav",
                language="en",
            ),
            RuntimeProviderConfig(),
        )
        assert response.transcript == "spoken"
        assert response.usage.audio_duration_ms == 1250

    async def test_openai_image_adapter(self):
        adapter = OpenAIImageAdapter(
            ProviderConfig(api_key="token"),
            client=FakeOpenAIClient(),
        )
        response = await adapter.generate(
            ImageGenerateRequest(model="gpt-image-1", prompt="cat"),
            RuntimeProviderConfig(),
        )
        assert response.images[0].url == "https://image.example/generated.png"
        assert response.usage is not None
        assert response.usage.input_tokens == 4
        assert response.usage.total_tokens == 4
        assert response.usage.estimated_cost == pytest.approx(0.12)



class TestProviderAdapterSync:
    def test_build_audio_file_wraps_pcm_as_wav(self):
        from llm_gateway.providers.shared.common import build_audio_file

        file_obj = build_audio_file(b"\x00\x00\x01\x00", "audio/pcm")
        assert file_obj.name == "audio.wav"
        with wave.open(file_obj, "rb") as wav_file:
            assert wav_file.getnchannels() == 1
            assert wav_file.getsampwidth() == 2
            assert wav_file.getframerate() == 24000
            assert wav_file.readframes(2) == b"\x00\x00\x01\x00"


class TestUsageInfoFromResult:
    """Cover usage_info_from_result: None / property / callable / missing."""

    def test_returns_none_when_result_is_none(self):
        from llm_gateway.providers.shared.common import usage_info_from_result

        assert usage_info_from_result(None) is None

    def test_extracts_usage_from_callable(self):
        from llm_gateway.providers.shared.common import usage_info_from_result

        usage_obj = SimpleNamespace(input_tokens=10, output_tokens=5, total_tokens=15)

        class Result:
            def usage(self):
                return usage_obj

        info = usage_info_from_result(Result())
        assert info is not None
        assert info.total_tokens == 15

    def test_extracts_usage_from_property(self):
        from llm_gateway.providers.shared.common import usage_info_from_result

        usage_obj = SimpleNamespace(input_tokens=2, output_tokens=3, total_tokens=5)

        class Result:
            usage = usage_obj

        info = usage_info_from_result(Result())
        assert info is not None
        assert info.total_tokens == 5

    def test_returns_none_when_usage_attribute_missing(self):
        from llm_gateway.providers.shared.common import usage_info_from_result

        class Result:
            pass

        assert usage_info_from_result(Result()) is None
