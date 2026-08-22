"""Memory Provider 注册表 — 注册/发现 + 配置驱动切换。"""

from __future__ import annotations

from .base import MemoryProvider


class MemoryProviderRegistry:
    """Memory Provider 注册/发现，支持配置驱动切换。

    用法::

        registry = MemoryProviderRegistry()
        registry.register(native_provider, default=True)
        registry.register(mem0_provider)

        # 按名称获取
        p = registry.get("native")

        # 获取默认 provider
        p = registry.get()
    """

    def __init__(self) -> None:
        self._providers: dict[str, MemoryProvider] = {}
        self._default: str | None = None

    def register(self, provider: MemoryProvider, *, default: bool = False) -> None:
        """注册一个 provider 实例。

        Args:
            provider: 实现了 MemoryProvider 协议的实例。
            default: 设为默认 provider。若注册表尚无默认则自动设为默认。
        """
        self._providers[provider.name] = provider
        if default or self._default is None:
            self._default = provider.name

    def get(self, name: str | None = None) -> MemoryProvider:
        """按名称获取 provider，不传则返回默认。

        Raises:
            KeyError: 指定名称未注册。
        """
        key = name or self._default
        if key is None or key not in self._providers:
            raise KeyError(f"Unknown memory provider: {key!r}")
        return self._providers[key]

    def list_providers(self) -> list[str]:
        """返回所有已注册 provider 名称。"""
        return list(self._providers.keys())

    @property
    def default_name(self) -> str | None:
        """当前默认 provider 名称。"""
        return self._default
