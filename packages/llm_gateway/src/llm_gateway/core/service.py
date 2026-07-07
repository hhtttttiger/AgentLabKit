from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import logging
from typing import Any, Awaitable, Callable, TypeVar, cast

from ..config import GatewaySettings
from ..errors import GatewayError, GatewayErrorCode
from ..model_catalog import CatalogError, CatalogErrorCode, ModelCatalogService, ModelResolver
from ..models import ModelRef
from ..model_catalog.retry_policy import RetryPolicy
from ..models import (
    Capability,
    EmbeddingGenerateRequest,
    EmbeddingGenerateResponse,
    ImageGenerateRequest,
    ImageGenerateResponse,
    ModelSummary,
    ProviderSummary,
    RealtimeClientEvent,
    RealtimeServerEvent,
    SpeechStreamChunk,
    SpeechStreamEvent,
    SpeechTranscribeRequest,
    SpeechTranscribeResponse,
    TextGenerateRequest,
    TextGenerateResponse,
    TextStreamEvent,
    UsageInfo,
)
from ..observability import GatewayObservability
from ..provider_runtime import RuntimeProviderConfig
from ..usage_info import accumulate_usage, normalize_usage
from ..usage.contracts import UsageAttemptRecord, UsageRequestRecord
from ..usage.recorder import NullUsageRecorder, UsageRecorder
from .adapters import EmbeddingAdapter, ImageAdapter, RealtimeAdapter, SpeechBatchAdapter, SpeechStreamAdapter, TextAdapter
from .circuit_breaker import CircuitBreaker
from .dispatch import _DispatchSession, _pricing_from_route
from .rate_limiter import TokenBucketRateLimiter
from .registry import ProviderRegistry

RequestModel = TypeVar("RequestModel")
ResponseModel = TypeVar("ResponseModel")
StreamEvent = TypeVar("StreamEvent")
AdapterType = TypeVar("AdapterType")

_CATALOG_ERROR_MAP = {
    CatalogErrorCode.BINDING_NOT_FOUND: GatewayErrorCode.BINDING_NOT_FOUND,
    CatalogErrorCode.MODEL_NOT_FOUND: GatewayErrorCode.MODEL_NOT_FOUND,
    CatalogErrorCode.MODEL_NAME_NOT_FOUND: GatewayErrorCode.MODEL_NAME_NOT_FOUND,
    CatalogErrorCode.MODEL_REF_AMBIGUOUS: GatewayErrorCode.MODEL_REF_AMBIGUOUS,
    CatalogErrorCode.NO_ENABLED_INSTANCE: GatewayErrorCode.NO_ENABLED_INSTANCE,
    CatalogErrorCode.FEATURE_REQUIREMENT_NOT_SATISFIED: GatewayErrorCode.FEATURE_REQUIREMENT_NOT_SATISFIED,
    CatalogErrorCode.UNSUPPORTED_CAPABILITY: GatewayErrorCode.UNSUPPORTED_CAPABILITY,
    CatalogErrorCode.PROVIDER_CONFLICT: GatewayErrorCode.PROVIDER_CONFLICT,
    CatalogErrorCode.CREDENTIAL_NOT_RESOLVED: GatewayErrorCode.CREDENTIAL_NOT_RESOLVED,
    CatalogErrorCode.CATALOG_UNAVAILABLE: GatewayErrorCode.CATALOG_UNAVAILABLE,
}

logger = logging.getLogger(__name__)


class GatewayService:
    def __init__(
        self,
        settings: GatewaySettings,
        registry: ProviderRegistry,
        resolver: ModelResolver,
        catalog_service: ModelCatalogService,
        *,
        observability: GatewayObservability | None = None,
        usage_recorder: UsageRecorder | None = None,
    ) -> None:
        self.settings = settings
        self.registry = registry
        self.resolver = resolver
        self.catalog_service = catalog_service
        self.observability = observability or GatewayObservability()
        self.usage_recorder: UsageRecorder = usage_recorder or NullUsageRecorder()
        self._rate_limiters: dict[str, TokenBucketRateLimiter] = {}
        self._circuit_breakers: dict[str, CircuitBreaker] = {}

    def _get_circuit_breaker(self, route) -> CircuitBreaker | None:
        """Return (or create) a per-instance circuit breaker, or ``None`` if unconfigured."""
        cfg = route.extra.get("circuit_breaker")
        if not cfg or not isinstance(cfg, dict):
            return None
        key = route.instance_key
        if key not in self._circuit_breakers:
            self._circuit_breakers[key] = CircuitBreaker(
                failure_threshold=int(cfg.get("failure_threshold", 5)),
                recovery_timeout=float(cfg.get("recovery_timeout", 30.0)),
                half_open_max_calls=int(cfg.get("half_open_max_calls", 1)),
            )
        return self._circuit_breakers.get(key)

    def _get_rate_limiter(self, route) -> TokenBucketRateLimiter | None:
        """Return (or create) a per-instance rate limiter, or ``None`` if unconfigured."""
        cfg = route.extra.get("rate_limit")
        if not cfg or not isinstance(cfg, dict):
            return None
        key = route.instance_key
        if key not in self._rate_limiters:
            rate = float(cfg.get("rate", 0))
            capacity = float(cfg.get("capacity", 0))
            if rate > 0 and capacity > 0:
                self._rate_limiters[key] = TokenBucketRateLimiter(rate, capacity)
        return self._rate_limiters.get(key)

    @staticmethod
    def _gateway_error_from_catalog(error: CatalogError, model_key: str | None) -> GatewayError:
        return GatewayError(
            _CATALOG_ERROR_MAP[error.code],
            error.message,
            provider=error.provider,
            model=model_key or error.model_key,
        )

    def _rewrite_request_model(self, request: Any, route) -> Any:
        timeout_ms = getattr(request, "timeout_ms", None) or route.default_timeout_ms
        return request.model_copy(
            update={
                "model": route.upstream_model_name(),
                "provider": route.provider,
                "timeout_ms": timeout_ms,
                "metadata": dict(getattr(request, "metadata", {})),
            }
        )

    @staticmethod
    def _rewrite_response_model(response: Any, logical_model: str, provider) -> Any:
        return response.model_copy(update={"model": logical_model, "provider": provider})

    async def _resolve_route(self, capability: Capability, model_key: str | None, provider, required_features=None, *, model_ref: ModelRef | None = None):
        routes, _ = await self._resolve_routes(capability, model_key, provider, required_features, model_ref=model_ref)
        return routes[0]

    async def _resolve_routes(
        self,
        capability: Capability,
        model_key: str | None,
        provider,
        required_features=None,
        *,
        model_ref: ModelRef | None = None,
    ) -> tuple[list, RetryPolicy]:
        """Resolve ordered candidate routes and the associated retry policy."""
        ref = model_ref or self._build_model_ref(model_key, capability)
        try:
            return await self.resolver.resolve(
                ref,
                capability_hint=capability,
                provider_hint=provider,
                required_features=required_features,
            )
        except CatalogError as exc:
            raise self._gateway_error_from_catalog(exc, model_key) from exc

    @staticmethod
    def _build_model_ref(model_key: str | None, capability: Capability) -> ModelRef:
        """Build a :class:`ModelRef` from the raw request *model* field.

        Resolution priority (matching the original auto-detect behaviour):
        1. ``None`` → use the default binding for *capability*
        2. Non-None string → delegate to :meth:`_auto_detect_ref`
        """
        if model_key is None:
            _DEFAULT_BINDINGS = {
                Capability.EMBEDDING: "gateway.default_embedding",
                Capability.TEXT: "gateway.default_text",
                Capability.SPEECH_BATCH: "gateway.default_speech_batch",
                Capability.SPEECH_STREAM: "gateway.default_speech_stream",
                Capability.IMAGE: "gateway.default_image",
                Capability.REALTIME: "gateway.default_realtime",
            }
            return ModelRef.binding(_DEFAULT_BINDINGS[capability])
        return _auto_detect_ref(model_key)

    @staticmethod
    def _default_binding_key(capability: Capability) -> str:
        _BINDING_MAP = {
            Capability.EMBEDDING: "gateway.default_embedding",
            Capability.TEXT: "gateway.default_text",
            Capability.SPEECH_BATCH: "gateway.default_speech_batch",
            Capability.SPEECH_STREAM: "gateway.default_speech_stream",
            Capability.IMAGE: "gateway.default_image",
            Capability.REALTIME: "gateway.default_realtime",
        }
        return _BINDING_MAP[capability]

    def _ensure_trace_id(self, request: RequestModel) -> RequestModel:
        trace_id = self.observability.ensure_trace_id(getattr(request, "trace_id", None))
        if getattr(request, "trace_id", None) == trace_id:
            return request
        return cast(RequestModel, request.model_copy(update={"trace_id": trace_id}))

    @staticmethod
    def _provider_label(provider: Any) -> str | None:
        if provider is None:
            return None
        return getattr(provider, "value", str(provider))

    def _log_start(
        self,
        *,
        capability: Capability,
        provider: Any,
        model: str,
        trace_id: str | None,
        event_kind: str,
    ) -> None:
        self.observability.log(
            logging.INFO,
            event_kind,
            trace_id=trace_id,
            provider=provider,
            model=model,
            capability=capability.value,
        )

    def _record_success(
        self,
        *,
        started_at: float,
        capability: Capability,
        provider: Any,
        model: str,
        trace_id: str | None,
        operation: str,
        event_count: int | None = None,
    ) -> None:
        duration_ms = self.observability.finish_request(
            started_at=started_at,
            operation=operation,
            capability=capability,
            provider=self._provider_label(provider),
            outcome="success",
        )
        fields: dict[str, object] = {
            "trace_id": trace_id,
            "provider": provider,
            "model": model,
            "capability": capability.value,
            "duration_ms": duration_ms,
        }
        if event_count is not None:
            fields["event_count"] = event_count
        self.observability.log(logging.INFO, "gateway.request.completed", **fields)

    def _record_failure(
        self,
        *,
        started_at: float,
        capability: Capability,
        provider: Any,
        model: str | None,
        trace_id: str | None,
        operation: str,
        error: Exception,
    ) -> None:
        duration_ms = self.observability.finish_request(
            started_at=started_at,
            operation=operation,
            capability=capability,
            provider=self._provider_label(provider),
            outcome="error",
        )
        self.observability.log(
            logging.ERROR,
            "gateway.request.failed",
            trace_id=trace_id,
            provider=provider,
            model=model,
            capability=capability.value,
            duration_ms=duration_ms,
            error_type=type(error).__name__,
            error_message=str(error),
        )

    @staticmethod
    def _calculate_cost(
        usage: UsageInfo | None,
        *,
        input_price_per_mtok: Decimal | None = None,
        output_price_per_mtok: Decimal | None = None,
        cache_write_price_per_mtok: Decimal | None = None,
        cache_read_price_per_mtok: Decimal | None = None,
    ) -> float | None:
        """Calculate cost from model pricing and token counts.

        Returns ``None`` when no pricing is configured, so the caller can
        fall back to any provider-reported ``estimated_cost``.
        """
        if usage is None:
            return None
        prices = (
            input_price_per_mtok,
            output_price_per_mtok,
            cache_write_price_per_mtok,
            cache_read_price_per_mtok,
        )
        if all(p is None for p in prices):
            return None
        input_tokens = usage.input_tokens or 0
        output_tokens = usage.output_tokens or 0
        cache_write = usage.cache_write_tokens or 0
        cache_read = usage.cache_read_tokens or 0
        non_cache_input = max(0, input_tokens - cache_write - cache_read)
        cost = Decimal("0")
        if prices[0] is not None:
            cost += Decimal(str(non_cache_input)) * prices[0]
        if prices[1] is not None:
            cost += Decimal(str(output_tokens)) * prices[1]
        if prices[2] is not None:
            cost += Decimal(str(cache_write)) * prices[2]
        if prices[3] is not None:
            cost += Decimal(str(cache_read)) * prices[3]
        return float(cost / Decimal("1000000"))

    async def _record_usage(
        self,
        *,
        request_id: str,
        model_key: str,
        instance_key: str,
        capability: Capability,
        success: bool,
        response: Any,
        started_at: float,
        error: Exception | None,
        usage: UsageInfo | None = None,
        attempt_no: int = 1,
        is_final: bool = True,
        total_attempts: int = 1,
        input_price_per_mtok: Decimal | None = None,
        output_price_per_mtok: Decimal | None = None,
        cache_write_price_per_mtok: Decimal | None = None,
        cache_read_price_per_mtok: Decimal | None = None,
    ) -> None:
        try:
            now = datetime.now(timezone.utc)
            duration_ms = int((self.observability.start_timer() - started_at) * 1000)
            if duration_ms < 0:
                duration_ms = 0
            started_dt = now - timedelta(milliseconds=duration_ms)

            usage = normalize_usage(usage or (getattr(response, "usage", None) if response else None))
            input_tokens = getattr(usage, "input_tokens", None) if usage else None
            output_tokens = getattr(usage, "output_tokens", None) if usage else None
            estimated_cost_raw = getattr(usage, "estimated_cost", None) if usage else None
            estimated_cost = float(estimated_cost_raw) if estimated_cost_raw is not None else None
            cache_write_tokens = getattr(usage, "cache_write_tokens", None) if usage else None
            cache_read_tokens = getattr(usage, "cache_read_tokens", None) if usage else None

            # Calculate cost from model pricing (takes priority over provider-reported cost).
            computed_cost = self._calculate_cost(
                usage,
                input_price_per_mtok=input_price_per_mtok,
                output_price_per_mtok=output_price_per_mtok,
                cache_write_price_per_mtok=cache_write_price_per_mtok,
                cache_read_price_per_mtok=cache_read_price_per_mtok,
            )
            final_cost = computed_cost if computed_cost is not None else estimated_cost
            error_code = error.code.value if isinstance(error, GatewayError) else ("UPSTREAM_FAILURE" if error else None)
            error_message = str(error) if error else None

            attempt = UsageAttemptRecord(
                request_id=request_id,
                model_key=model_key,
                instance_key=instance_key,
                attempt_no=attempt_no,
                success=success,
                error_code=error_code,
                error_message=error_message,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                estimated_cost=final_cost,
                cache_write_tokens=cache_write_tokens,
                cache_read_tokens=cache_read_tokens,
                duration_ms=duration_ms,
                started_at_utc=started_dt,
                completed_at_utc=now,
            )
            await self.usage_recorder.record_attempt(attempt)

            # Only write the request-level summary on the final attempt.
            if is_final:
                request_record = UsageRequestRecord(
                    request_id=request_id,
                    model_key=model_key,
                    capability=capability.value,
                    success=success,
                    attempt_count=total_attempts,
                    final_instance_key=instance_key if success else None,
                    error_code=error_code,
                    error_message=error_message,
                    total_input_tokens=input_tokens or 0,
                    total_output_tokens=output_tokens or 0,
                    total_estimated_cost=final_cost or 0.0,
                    cache_write_tokens=cache_write_tokens or 0,
                    cache_read_tokens=cache_read_tokens or 0,
                    total_duration_ms=duration_ms,
                    started_at_utc=started_dt,
                    completed_at_utc=now,
                )
                await self.usage_recorder.record_request(request_record)
        except Exception:
            logger.warning("Failed to prepare or record usage", exc_info=True)

    async def _dispatch_unary(
        self,
        *,
        capability: Capability,
        request: RequestModel,
        invoker: Callable[[AdapterType, RequestModel, RuntimeProviderConfig], Awaitable[ResponseModel]],
    ) -> ResponseModel:
        request = self._ensure_trace_id(request)
        candidates, retry_policy = await self._resolve_routes(
            capability,
            request.model,
            request.provider,
            getattr(request, "required_features", None),
            model_ref=getattr(request, "model_ref", None),
        )
        trace_id = getattr(request, "trace_id", None)
        session = _DispatchSession(self, capability, candidates, retry_policy, trace_id, request)

        for attempt_no, route in enumerate(candidates, start=1):
            adapter, upstream_request = session.prepare_route(route)
            self._log_start(
                capability=capability,
                provider=route.provider,
                model=route.model_key,
                trace_id=trace_id,
                event_kind="gateway.request.started",
            )
            breaker, limiter = await session.enter_route(route)
            timeout_ms = getattr(upstream_request, "timeout_ms", None) or route.default_timeout_ms
            try:
                async with asyncio.timeout(timeout_ms / 1000):
                    response = await invoker(cast(AdapterType, adapter), upstream_request, route.runtime_config)
            except asyncio.TimeoutError as exc:
                raise GatewayError(
                    GatewayErrorCode.PROVIDER_TIMEOUT,
                    f"Request timed out after {timeout_ms}ms",
                    provider=route.provider,
                    model=route.model_key,
                ) from exc
            except Exception as exc:
                if await session.handle_failure(route, exc, attempt_no, breaker=breaker):
                    continue
                raise

            if breaker:
                await breaker.record_success()
            self._record_success(
                started_at=session.started_at,
                capability=capability,
                provider=route.provider,
                model=route.model_key,
                trace_id=trace_id,
                operation=capability.value,
            )
            await self._record_usage(
                request_id=trace_id or "unknown",
                model_key=route.model_key,
                instance_key=route.instance_key,
                capability=capability,
                success=True,
                response=response,
                started_at=session.started_at,
                error=None,
                attempt_no=attempt_no,
                is_final=True,
                total_attempts=attempt_no,
                **_pricing_from_route(route),
            )
            return self._rewrite_response_model(response, route.model_key, route.provider)

        raise session.last_error

    async def _dispatch_stream(
        self,
        *,
        capability: Capability,
        request: RequestModel,
        invoker: Callable[[AdapterType, RequestModel, RuntimeProviderConfig], AsyncIterator[StreamEvent]],
    ) -> AsyncIterator[StreamEvent]:
        request = self._ensure_trace_id(request)
        candidates, retry_policy = await self._resolve_routes(
            capability,
            request.model,
            request.provider,
            getattr(request, "required_features", None),
            model_ref=getattr(request, "model_ref", None),
        )
        trace_id = getattr(request, "trace_id", None)
        session = _DispatchSession(self, capability, candidates, retry_policy, trace_id, request)

        for attempt_no, route in enumerate(candidates, start=1):
            adapter, upstream_request = session.prepare_route(route)
            event_count = 0
            accumulated_usage: UsageInfo | None = None
            self._log_start(
                capability=capability,
                provider=route.provider,
                model=route.model_key,
                trace_id=trace_id,
                event_kind="gateway.stream.started",
            )
            breaker, limiter = await session.enter_route(route)
            timeout_ms = getattr(upstream_request, "timeout_ms", None) or route.default_timeout_ms
            try:
                async with asyncio.timeout(timeout_ms / 1000):
                    async for event in invoker(cast(AdapterType, adapter), upstream_request, route.runtime_config):
                        event_count += 1
                        accumulated_usage = accumulate_usage(accumulated_usage, getattr(event, "usage", None))
                        rewritten = self._rewrite_response_model(event, route.model_key, route.provider)
                        yield rewritten.model_copy(update={"instance_key": route.instance_key})
            except asyncio.TimeoutError as exc:
                raise GatewayError(
                    GatewayErrorCode.PROVIDER_TIMEOUT,
                    f"Stream timed out after {timeout_ms}ms",
                    provider=route.provider,
                    model=route.model_key,
                ) from exc
            except Exception as exc:
                if await session.handle_failure(route, exc, attempt_no, usage=accumulated_usage, breaker=breaker):
                    continue
                raise

            await session.handle_success(route, usage=accumulated_usage, event_count=event_count, breaker=breaker)
            return

        raise session.last_error

    async def generate_embedding(self, request: EmbeddingGenerateRequest) -> EmbeddingGenerateResponse:
        return await self._dispatch_unary(
            capability=Capability.EMBEDDING,
            request=request,
            invoker=lambda adapter, upstream_request, runtime_config: cast(
                EmbeddingAdapter,
                adapter,
            ).generate(
                upstream_request,
                runtime_config,
            ),
        )

    async def generate_text(self, request: TextGenerateRequest) -> TextGenerateResponse:
        return await self._dispatch_unary(
            capability=Capability.TEXT,
            request=request,
            invoker=lambda adapter, upstream_request, runtime_config: cast(TextAdapter, adapter).generate(
                upstream_request,
                runtime_config,
            ),
        )

    async def generate_text_stream(self, request: TextGenerateRequest) -> AsyncIterator[TextStreamEvent]:
        async for event in self._dispatch_stream(
            capability=Capability.TEXT,
            request=request,
            invoker=lambda adapter, upstream_request, runtime_config: cast(TextAdapter, adapter).generate_stream(
                upstream_request,
                runtime_config,
            ),
        ):
            yield event

    async def transcribe_speech(self, request: SpeechTranscribeRequest) -> SpeechTranscribeResponse:
        return await self._dispatch_unary(
            capability=Capability.SPEECH_BATCH,
            request=request,
            invoker=lambda adapter, upstream_request, runtime_config: cast(
                SpeechBatchAdapter,
                adapter,
            ).transcribe(
                upstream_request,
                runtime_config,
            ),
        )

    async def transcribe_speech_stream(
        self,
        chunks: AsyncIterator[SpeechStreamChunk],
        model_key: str | None,
        provider,
    ) -> AsyncIterator[SpeechStreamEvent]:
        async for event in self._dispatch_stream_from_events(
            events=chunks,
            capability=Capability.SPEECH_STREAM,
            model_key=model_key,
            provider=provider,
            rewrite_first=self._rewrite_speech_chunk,
            rewrite_event=self._rewrite_speech_chunk,
            invoke_stream=lambda adapter, traced, config: cast(SpeechStreamAdapter, adapter).transcribe_stream(traced, config),
        ):
            yield event

    async def _rewrite_speech_chunk(
        self,
        chunk: SpeechStreamChunk,
        route: Any,
        trace_id: str,
        _transport_cache: dict[str, str] | None = None,
    ) -> SpeechStreamChunk:
        if _transport_cache is None:
            _transport_cache = {}
        metadata = await _rewrite_transport_model(dict(chunk.metadata), self._resolve_route, _transport_cache)
        return chunk.model_copy(
            update={
                "trace_id": trace_id if chunk.trace_id is None else chunk.trace_id,
                "model": route.upstream_model_name(),
                "provider": route.provider,
                "metadata": metadata,
            },
        )

    async def generate_image(self, request: ImageGenerateRequest) -> ImageGenerateResponse:
        return await self._dispatch_unary(
            capability=Capability.IMAGE,
            request=request,
            invoker=lambda adapter, upstream_request, runtime_config: cast(ImageAdapter, adapter).generate(
                upstream_request,
                runtime_config,
            ),
        )

    async def run_realtime_session(
        self,
        events: AsyncIterator[RealtimeClientEvent],
        model_key: str | None,
        provider,
    ) -> AsyncIterator[RealtimeServerEvent]:
        async for event in self._dispatch_stream_from_events(
            events=events,
            capability=Capability.REALTIME,
            model_key=model_key,
            provider=provider,
            rewrite_first=self._rewrite_realtime_event,
            rewrite_event=self._rewrite_realtime_event,
            invoke_stream=lambda adapter, traced, config: cast(RealtimeAdapter, adapter).session(traced, config),
        ):
            yield event

    @staticmethod
    async def _rewrite_realtime_event(
        event: RealtimeClientEvent,
        route: Any,
        trace_id: str,
    ) -> RealtimeClientEvent:
        return event.model_copy(
            update={
                "trace_id": trace_id if event.trace_id is None else event.trace_id,
                "model": route.upstream_model_name(),
                "provider": route.provider,
            },
        )

    async def _dispatch_stream_from_events(
        self,
        *,
        events: AsyncIterator[Any],
        capability: Capability,
        model_key: str | None,
        provider: Any,
        rewrite_first: Callable[[Any, Any, str], Any],
        rewrite_event: Callable[[Any, Any, str], Any],
        invoke_stream: Callable[[Any, AsyncIterator[Any], Any], AsyncIterator[Any]],
    ) -> AsyncIterator[Any]:
        """Generic streaming dispatch for protocols that send events (not request objects).

        Peeks the first event to resolve the route, rewrites all events with
        upstream model names, and delegates to the adapter.  Metrics and usage
        recording are handled inline.
        """
        started_at = self.observability.start_timer()
        try:
            first_event = await anext(events)
        except StopAsyncIteration:
            return

        route = await self._resolve_route(
            capability,
            model_key or getattr(first_event, "model", None),
            provider or getattr(first_event, "provider", None),
            getattr(first_event, "required_features", None),
            model_ref=getattr(first_event, "model_ref", None),
        )
        adapter = self.registry.resolve_adapter(capability, provider=route.provider)
        trace_id = self.observability.ensure_trace_id(getattr(first_event, "trace_id", None))

        first_rewritten = await rewrite_first(first_event, route, trace_id)

        async def traced_events() -> AsyncIterator[Any]:
            yield first_rewritten
            async for event in events:
                yield await rewrite_event(event, route, trace_id)

        # Use the same fault-tolerance gates as regular dispatch paths.
        breaker = self._get_circuit_breaker(route)
        if breaker and not await breaker.allow_request():
            raise GatewayError(
                GatewayErrorCode.UPSTREAM_ERROR,
                f"Circuit breaker open for instance {route.instance_key}",
                provider=route.provider,
                model=route.model_key,
            )
        limiter = self._get_rate_limiter(route)
        if limiter:
            await limiter.acquire()

        event_count = 0
        accumulated_usage: UsageInfo | None = None
        self._log_start(
            capability=capability,
            provider=route.provider,
            model=route.model_key,
            trace_id=trace_id,
            event_kind="gateway.stream.started",
        )
        try:
            async for event in invoke_stream(adapter, traced_events(), route.runtime_config):
                event_count += 1
                accumulated_usage = accumulate_usage(accumulated_usage, getattr(event, "usage", None))
                yield event.model_copy(update={"model": route.model_key, "provider": route.provider})
        except Exception as exc:
            if breaker:
                await breaker.record_failure()
            self._record_failure(
                started_at=started_at,
                capability=capability,
                provider=route.provider,
                model=route.model_key,
                trace_id=trace_id,
                operation=capability.value,
                error=exc,
            )
            await self._record_usage(
                request_id=trace_id or "unknown",
                model_key=route.model_key,
                instance_key=route.instance_key,
                capability=capability,
                success=False,
                response=None,
                started_at=started_at,
                error=exc,
                usage=accumulated_usage,
                **_pricing_from_route(route),
            )
            raise

        if breaker:
            await breaker.record_success()
        self._record_success(
            started_at=started_at,
            capability=capability,
            provider=route.provider,
            model=route.model_key,
            trace_id=trace_id,
            operation=capability.value,
            event_count=event_count,
        )
        await self._record_usage(
            request_id=trace_id or "unknown",
            model_key=route.model_key,
            instance_key=route.instance_key,
            capability=capability,
            success=True,
            response=None,
            started_at=started_at,
            error=None,
            usage=accumulated_usage,
            **_pricing_from_route(route),
        )

    def providers(self) -> ProviderSummary:
        return ProviderSummary(providers=self.registry.list_provider_capabilities())

    async def models(self) -> ModelSummary:
        return ModelSummary(models=await self.catalog_service.list_models())


def _auto_detect_ref(raw: str) -> ModelRef:
    """Auto-detect the resolution strategy for a raw model string.

    Since we don't have the snapshot here, we pass the string as ``model_key``
    and let the resolver handle fallback to binding_key detection (existing
    behaviour in ``ModelResolver.resolve_candidates``).  This preserves full
    backward compatibility for callers that pass binding keys via the ``model``
    field (e.g. ``agent_runtime``).
    """
    return ModelRef.model(raw)


async def _rewrite_transport_model(
    metadata: dict[str, Any],
    resolve_route_fn: Any,
    cache: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Rewrite ``realtime_transport_model`` in metadata to its upstream name.

    Results are cached per *cache* dict to avoid repeated route resolution
    when the same transport model appears across multiple streaming chunks.
    """
    transport_model = metadata.get("realtime_transport_model")
    if transport_model:
        if cache is not None and transport_model in cache:
            metadata["realtime_transport_model"] = cache[transport_model]
            return metadata
        try:
            route = await resolve_route_fn(Capability.REALTIME, transport_model, None)
            upstream = route.upstream_model_name()
            if cache is not None:
                cache[transport_model] = upstream
            metadata["realtime_transport_model"] = upstream
        except Exception:
            pass
    return metadata
