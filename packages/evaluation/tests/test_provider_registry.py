"""ProviderRegistry 单元测试。"""

from __future__ import annotations

import pytest

from evaluation.providers.registry import ProviderRegistry
from evaluation.providers.base import EvalProvider


# ── 辅助 mock ────────────────────────────────────────────────────────


class _MockProvider:
    """最小化 EvalProvider mock。"""

    def __init__(self, name: str, metrics: list[str] | None = None):
        self.name = name
        self._metrics = metrics or []

    def get_metric(self, metric_name: str):
        raise NotImplementedError

    def list_metrics(self) -> list[str]:
        return self._metrics

    async def evaluate(self, cases, metrics, config):
        raise NotImplementedError


# ── 测试 ─────────────────────────────────────────────────────────────


class TestProviderRegistry:
    def test_register_and_get(self):
        reg = ProviderRegistry()
        p = _MockProvider("ragas")
        reg.register(p)

        assert reg.get("ragas") is p
        assert reg.list_providers() == ["ragas"]

    def test_first_registered_becomes_default(self):
        reg = ProviderRegistry()
        p1 = _MockProvider("ragas")
        p2 = _MockProvider("deepeval")
        reg.register(p1)
        reg.register(p2)

        assert reg.default_name == "ragas"
        assert reg.get() is p1

    def test_explicit_default(self):
        reg = ProviderRegistry()
        p1 = _MockProvider("ragas")
        p2 = _MockProvider("deepeval")
        reg.register(p1)
        reg.register(p2, default=True)

        assert reg.default_name == "deepeval"
        assert reg.get() is p2

    def test_get_unknown_raises_key_error(self):
        reg = ProviderRegistry()
        with pytest.raises(KeyError, match="Unknown evaluation provider"):
            reg.get("nonexistent")

    def test_get_none_default_when_empty(self):
        reg = ProviderRegistry()
        with pytest.raises(KeyError, match="Unknown evaluation provider"):
            reg.get()

    def test_list_all_metrics(self):
        reg = ProviderRegistry()
        p1 = _MockProvider("ragas", ["faithfulness", "answer_relevancy"])
        p2 = _MockProvider("deepeval", ["geval"])
        reg.register(p1)
        reg.register(p2)

        all_metrics = reg.list_all_metrics()
        assert all_metrics == {
            "ragas": ["faithfulness", "answer_relevancy"],
            "deepeval": ["geval"],
        }

    def test_register_overwrites_same_name(self):
        reg = ProviderRegistry()
        p1 = _MockProvider("ragas", ["a"])
        p2 = _MockProvider("ragas", ["b"])
        reg.register(p1)
        reg.register(p2)

        assert reg.get("ragas") is p2
        assert reg.list_providers() == ["ragas"]

    def test_default_name_property(self):
        reg = ProviderRegistry()
        assert reg.default_name is None
        reg.register(_MockProvider("ragas"))
        assert reg.default_name == "ragas"
