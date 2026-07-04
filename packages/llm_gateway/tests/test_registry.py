from __future__ import annotations

import pytest

from llm_gateway.core.registry import CapabilityRegistration, ProviderAdapterBundle, ProviderRegistry
from llm_gateway.errors import GatewayError, GatewayErrorCode
from llm_gateway.models import Capability, CapabilityStatus, ProviderId


class TestRegistry:
    def setup_method(self) -> None:
        self.registry = ProviderRegistry()
        self.registry.register(ProviderAdapterBundle(provider=ProviderId.OPENAI, text=object()))

    def test_list_provider_capabilities_returns_declared_adapters(self):
        providers = self.registry.list_provider_capabilities()
        assert len(providers) == 1
        assert providers[0].provider == ProviderId.OPENAI
        assert providers[0].capabilities == {Capability.TEXT}
        assert providers[0].capability_matrix[0].status == CapabilityStatus.SUPPORTED

    def test_resolve_adapter_rejects_wrong_capability(self):
        with pytest.raises(GatewayError) as exc:
            self.registry.resolve_adapter(
                Capability.IMAGE,
                provider=ProviderId.OPENAI,
            )
        assert exc.value.code == GatewayErrorCode.UNSUPPORTED_CAPABILITY

    def test_provider_matrix_can_explicitly_mark_unsupported_capability(self):
        registry = ProviderRegistry()
        registry.register(
            ProviderAdapterBundle(
                provider=ProviderId.OPENAI,
                text=object(),
                capability_matrix={
                    Capability.REALTIME: CapabilityRegistration(
                        status=CapabilityStatus.UNSUPPORTED,
                        reason="not enabled",
                    )
                },
            )
        )
        provider = registry.list_provider_capabilities()[0]
        realtime = next(
            item for item in provider.capability_matrix if item.capability == Capability.REALTIME
        )
        assert realtime.status == CapabilityStatus.UNSUPPORTED
        assert realtime.reason == "not enabled"
