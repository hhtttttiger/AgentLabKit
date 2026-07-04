from __future__ import annotations

from dataclasses import dataclass, field

from ..errors import GatewayError, GatewayErrorCode
from ..models import Capability, CapabilityStatus, CapabilitySupport, ProviderCapabilities, ProviderId
from .adapters import EmbeddingAdapter, ImageAdapter, RealtimeAdapter, SpeechBatchAdapter, SpeechStreamAdapter, TextAdapter


@dataclass(frozen=True, slots=True)
class CapabilityRegistration:
    status: CapabilityStatus
    reason: str | None = None


@dataclass(slots=True)
class ProviderAdapterBundle:
    provider: ProviderId
    embedding: EmbeddingAdapter | None = None
    text: TextAdapter | None = None
    speech_batch: SpeechBatchAdapter | None = None
    speech_stream: SpeechStreamAdapter | None = None
    image: ImageAdapter | None = None
    realtime: RealtimeAdapter | None = None
    capabilities: set[Capability] = field(default_factory=set)
    capability_matrix: dict[Capability, CapabilityRegistration] = field(default_factory=dict)

    def adapter_for(self, capability: Capability) -> object | None:
        return {
            Capability.EMBEDDING: self.embedding,
            Capability.TEXT: self.text,
            Capability.SPEECH_BATCH: self.speech_batch,
            Capability.SPEECH_STREAM: self.speech_stream,
            Capability.IMAGE: self.image,
            Capability.REALTIME: self.realtime,
        }[capability]


class ProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[ProviderId, ProviderAdapterBundle] = {}

    def register(self, bundle: ProviderAdapterBundle) -> None:
        implemented = {
            capability
            for capability in Capability
            if bundle.adapter_for(capability) is not None
        }
        bundle.capabilities = implemented
        matrix: dict[Capability, CapabilityRegistration] = {}
        for capability in Capability:
            registration = bundle.capability_matrix.get(capability)
            if registration is None:
                registration = CapabilityRegistration(
                    status=(
                        CapabilityStatus.SUPPORTED
                        if capability in implemented
                        else CapabilityStatus.UNSUPPORTED
                    )
                )
            matrix[capability] = registration
        bundle.capability_matrix = matrix
        bundle.capabilities = {
            capability
            for capability, registration in matrix.items()
            if registration.status == CapabilityStatus.SUPPORTED
            and bundle.adapter_for(capability) is not None
        }
        self._providers[bundle.provider] = bundle

    def list_provider_capabilities(self) -> list[ProviderCapabilities]:
        return [
            ProviderCapabilities(
                provider=provider,
                capabilities=bundle.capabilities,
                capability_matrix=[
                    CapabilitySupport(
                        capability=capability,
                        status=registration.status,
                        reason=registration.reason,
                    )
                    for capability, registration in bundle.capability_matrix.items()
                ],
            )
            for provider, bundle in self._providers.items()
        ]

    def resolve_adapter(
        self,
        capability: Capability,
        *,
        provider: ProviderId,
    ) -> object:
        bundle = self._providers.get(provider)
        if bundle is None:
            raise GatewayError(
                GatewayErrorCode.PROVIDER_NOT_FOUND,
                f"Provider '{provider}' is not registered.",
                provider=provider,
            )
        adapter = bundle.adapter_for(capability)
        if adapter is None:
            raise GatewayError(
                GatewayErrorCode.UNSUPPORTED_CAPABILITY,
                f"Provider '{provider}' does not implement capability '{capability}'.",
                provider=provider,
            )
        return adapter
