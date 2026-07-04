from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Capability(str, Enum):
    TEXT = "text"
    EMBEDDING = "embedding"
    SPEECH_BATCH = "speech_batch"
    SPEECH_STREAM = "speech_stream"
    IMAGE = "image"
    REALTIME = "realtime"


class CapabilityStatus(str, Enum):
    SUPPORTED = "supported"
    UNSUPPORTED = "unsupported"


class ProviderId(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class UsageInfo(BaseModel):
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    audio_duration_ms: int | None = None
    estimated_cost: float | None = None
    cache_write_tokens: int | None = None
    cache_read_tokens: int | None = None


class ErrorPayload(BaseModel):
    code: str
    message: str
    provider: str | None = None
    model: str | None = None


class ModelDefinition(BaseModel):
    model_key: str
    provider: ProviderId
    provider_model_name: str
    provider_deployment_name: str | None = None
    capabilities: set[Capability]
    enabled: bool = True
    region: str | None = None
    default_timeout_ms: int = 30_000

    def upstream_model_name(self) -> str:
        return self.provider_deployment_name or self.provider_model_name


class GatewayMetadata(BaseModel):
    trace_id: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)
    timeout_ms: int | None = None


class TextGenerateRequest(BaseModel):
    provider: ProviderId | None = None
    model: str | None = None
    prompt: str
    trace_id: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)
    required_features: dict[str, Any] = Field(default_factory=dict)
    timeout_ms: int | None = None
    temperature: float | None = None
    max_output_tokens: int | None = None
    structured: bool = False


class TextGenerateResponse(BaseModel):
    provider: ProviderId
    model: str
    text: str
    finish_reason: str | None = None
    usage: UsageInfo | None = None
    error: ErrorPayload | None = None


class EmbeddingGenerateRequest(BaseModel):
    provider: ProviderId | None = None
    model: str | None = None
    input: str
    trace_id: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)
    required_features: dict[str, Any] = Field(default_factory=dict)
    timeout_ms: int | None = None
    dimensions: int | None = None


class EmbeddingGenerateResponse(BaseModel):
    provider: ProviderId
    model: str
    embedding: list[float]
    dimensions: int
    usage: UsageInfo | None = None
    error: ErrorPayload | None = None


class TextStreamEvent(BaseModel):
    event_type: str
    provider: ProviderId
    model: str
    instance_key: str | None = None
    delta: str | None = None
    text: str | None = None
    finish_reason: str | None = None
    usage: UsageInfo | None = None
    error: ErrorPayload | None = None


class SpeechTranscribeRequest(BaseModel):
    provider: ProviderId | None = None
    model: str | None = None
    audio: bytes
    mime_type: str
    language: str | None = None
    trace_id: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)
    required_features: dict[str, Any] = Field(default_factory=dict)


class SpeechTranscribeResponse(BaseModel):
    provider: ProviderId
    model: str
    transcript: str
    language: str | None = None
    usage: UsageInfo | None = None
    error: ErrorPayload | None = None


class SpeechStreamChunk(BaseModel):
    provider: ProviderId | None = None
    model: str | None = None
    audio_chunk: bytes
    mime_type: str
    end_of_audio: bool = False
    language: str | None = None
    trace_id: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)
    required_features: dict[str, Any] = Field(default_factory=dict)


class SpeechStreamEvent(BaseModel):
    event_type: str
    provider: ProviderId
    model: str
    transcript: str | None = None
    is_final: bool = False
    usage: UsageInfo | None = None
    error: ErrorPayload | None = None


class ImageGenerateRequest(BaseModel):
    provider: ProviderId | None = None
    model: str | None = None
    prompt: str
    size: str = "1024x1024"
    count: int = 1
    format: str = "url"
    trace_id: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)
    required_features: dict[str, Any] = Field(default_factory=dict)


class GeneratedImage(BaseModel):
    url: str | None = None
    data_base64: str | None = None
    mime_type: str | None = None


class ImageGenerateResponse(BaseModel):
    provider: ProviderId
    model: str
    images: list[GeneratedImage]
    usage: UsageInfo | None = None
    error: ErrorPayload | None = None


class RealtimeSessionRequest(BaseModel):
    provider: ProviderId | None = None
    model: str | None = None
    trace_id: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)
    translation_mode: bool = False


class RealtimeClientEvent(BaseModel):
    event_type: str
    provider: ProviderId | None = None
    model: str | None = None
    text: str | None = None
    audio_chunk: bytes | None = None
    metadata: dict[str, str] = Field(default_factory=dict)
    required_features: dict[str, Any] = Field(default_factory=dict)
    trace_id: str | None = None
    tools: list[dict[str, Any]] = Field(default_factory=list)
    tool_choice: str | None = None
    tool_call_id: str | None = None
    tool_output: str | None = None


class RealtimeServerEvent(BaseModel):
    event_type: str
    provider: ProviderId
    model: str
    text: str | None = None
    transcript: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)
    is_final: bool = False
    usage: UsageInfo | None = None
    error: ErrorPayload | None = None
    audio_chunk: bytes | None = None
    mime_type: str | None = None
    sequence: int | None = None
    state: str | None = None
    detail: str | None = None
    tool_name: str | None = None
    tool_call_id: str | None = None
    tool_arguments: dict[str, Any] = Field(default_factory=dict)


class ProviderCapabilities(BaseModel):
    provider: ProviderId
    capabilities: set[Capability]
    capability_matrix: list["CapabilitySupport"] = Field(default_factory=list)


class CapabilitySupport(BaseModel):
    capability: Capability
    status: CapabilityStatus
    reason: str | None = None


class ProviderSummary(BaseModel):
    providers: list[ProviderCapabilities]


class CatalogModelSummary(BaseModel):
    model_key: str
    display_name: str
    enabled: bool = True
    capabilities: set[Capability] = Field(default_factory=set)
    providers: set[ProviderId] = Field(default_factory=set)
    binding_keys: list[str] = Field(default_factory=list)


class ModelSummary(BaseModel):
    models: list[CatalogModelSummary]


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "agent-service-gateway"
    version: str = "0.1.0"


class UploadSpeechRequest(BaseModel):
    model: str | None = None
    provider: ProviderId | None = None
    language: str | None = None
    trace_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
