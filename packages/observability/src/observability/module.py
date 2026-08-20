from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from .config import ObservabilitySettings
from .publisher import AsyncTracePublisher
from .trace_store import PostgresTraceStore, TraceStore

if TYPE_CHECKING:
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.trace import Tracer


@dataclass(slots=True)
class ObservabilityModule:
    settings: ObservabilitySettings
    trace_store: TraceStore
    tracer_provider: Any  # opentelemetry.sdk.trace.TracerProvider
    tracer: Any  # opentelemetry.trace.Tracer
    publisher: AsyncTracePublisher
    span_processor: Any = None  # TraceBufferSpanProcessor | None

    async def start(self) -> None:
        await self.publisher.start()

    async def shutdown(self) -> None:
        self.tracer_provider.force_flush(
            timeout_millis=int(self.settings.flush_timeout_seconds * 1_000),
        )
        await self.publisher.shutdown()
        self.tracer_provider.shutdown()

    def ingestion_health(self) -> dict[str, Any]:
        return {
            **self.publisher.snapshot(),
            **(self.span_processor.snapshot() if self.span_processor else {}),
        }

    def get_tracer(self, name: str, version: str = "2.0.0") -> Any:
        from opentelemetry.trace import NoOpTracer

        if not self.settings.enabled:
            return NoOpTracer()
        return self.tracer_provider.get_tracer(name, version)


def create_observability_module(
    *,
    session_factory,
    queue_backend: Any | None = None,
    settings: ObservabilitySettings | None = None,
    service_name: str = "agentlabkit",
) -> ObservabilityModule:
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.trace import NoOpTracer

    from .span_processor import TraceBufferSpanProcessor

    resolved = settings or ObservabilitySettings()
    publisher = AsyncTracePublisher(queue_backend, resolved)
    provider = TracerProvider(
        resource=Resource.create(
            {
                "service.name": service_name,
                "telemetry.sdk.language": "python",
            },
        ),
    )
    processor = TraceBufferSpanProcessor(publisher, resolved) if resolved.enabled else None
    if processor is not None:
        provider.add_span_processor(processor)
    return ObservabilityModule(
        settings=resolved,
        trace_store=PostgresTraceStore(session_factory),
        tracer_provider=provider,
        tracer=(
            provider.get_tracer("agentlabkit", "2.0.0")
            if resolved.enabled
            else NoOpTracer()
        ),
        publisher=publisher,
        span_processor=processor,
    )
