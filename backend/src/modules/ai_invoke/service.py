"""Invoke service for model operations and agent option queries.

Agent execution orchestration lives in application.ExecuteAgent.
"""
from __future__ import annotations

import json
import time
from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from modules.agent.models import AgentDefinition


class InvokeService:
    def __init__(self, *, gateway_service: Any, agent_runtime: Any,
                 agent_definition_loader: Any, session_factory: Any) -> None:
        self._gateway = gateway_service

    async def list_agent_options(self, db: AsyncSession) -> list[dict]:
        result = await db.execute(
            select(AgentDefinition)
            .where(AgentDefinition.is_enabled == True,
                   AgentDefinition.published_version != None)
            .order_by(AgentDefinition.display_name)
        )
        return [{
            "agentKey": a.agent_key, "displayName": a.display_name,
            "description": a.description, "icon": a.icon,
            "publishedVersionNumber": a.published_version,
        } for a in result.scalars().all()]

    async def generate_text(self, *, model_id: str, message: str,
                            system_prompt: str | None = None) -> dict:
        from llm_gateway.models import TextGenerateRequest
        result = await self._gateway.generate_text(
            TextGenerateRequest(model=model_id, prompt=self._build_prompt(message, system_prompt))
        )
        return {"content": result.text, "model": result.model, "provider": result.provider,
                "usage": result.usage.model_dump() if result.usage else None}

    async def generate_text_sse_stream(self, *, model_id: str, message: str,
                                       system_prompt: str | None = None) -> AsyncGenerator[str, None]:
        from llm_gateway.models import TextGenerateRequest
        try:
            async for event in self._gateway.generate_text_stream(
                TextGenerateRequest(model=model_id, prompt=self._build_prompt(message, system_prompt))
            ):
                yield f"data: {json.dumps({'content': event.delta or '', 'done': event.event_type == 'finished'}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'content': str(exc), 'done': True}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"

    async def generate_text_test_sse_stream(self, *, model_id: str, message: str,
                                            system_prompt: str | None = None) -> AsyncGenerator[str, None]:
        from llm_gateway.models import TextGenerateRequest
        started = time.perf_counter(); ttft = None; first = False
        instance = provider = model = finish = None; usage = None
        try:
            async for event in self._gateway.generate_text_stream(
                TextGenerateRequest(model=model_id, prompt=self._build_prompt(message, system_prompt))
            ):
                instance = event.instance_key or instance
                provider = event.provider.value if event.provider is not None else provider
                model = event.model or model; finish = event.finish_reason or finish
                usage = event.usage or usage
                if event.delta:
                    if not first: ttft = int((time.perf_counter() - started) * 1000); first = True
                    yield f"data: {json.dumps({'type': 'content', 'content': event.delta, 'instance_key': instance, 'provider': provider, 'model': model}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'type': 'stats', 'ttft_ms': ttft, 'total_ms': int((time.perf_counter() - started) * 1000), 'instance_key': instance, 'provider': provider, 'model': model, 'finish_reason': finish, 'input_tokens': usage.input_tokens if usage else None, 'output_tokens': usage.output_tokens if usage else None, 'total_tokens': usage.total_tokens if usage else None}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'type': 'error', 'message': str(exc), 'ttft_ms': ttft, 'total_ms': int((time.perf_counter() - started) * 1000)}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"

    async def generate_embedding_test(self, *, model_id: str, text: str,
                                      dimensions: int | None = None) -> dict:
        from llm_gateway.models import EmbeddingGenerateRequest
        started = time.perf_counter()
        try:
            result = await self._gateway.generate_embedding(
                EmbeddingGenerateRequest(model=model_id, input=text, dimensions=dimensions)
            )
        except Exception as exc:
            raise EmbeddingError(message=str(exc), code=getattr(getattr(exc, 'code', None), 'value', None),
                                  latency_ms=int((time.perf_counter() - started) * 1000)) from exc
        embedding = result.embedding
        return {"success": True, "provider": result.provider.value if result.provider else None,
                "model": result.model, "dimensions": result.dimensions,
                "vectorPreview": embedding[:10], "vectorPreviewTruncated": len(embedding) > 10,
                "usage": result.usage.model_dump() if result.usage else None,
                "latencyMs": int((time.perf_counter() - started) * 1000)}

    @staticmethod
    def _build_prompt(message: str, system_prompt: str | None) -> str:
        return f"System: {system_prompt}\n\nUser: {message}" if system_prompt else message


class AgentNotFoundError(Exception):
    def __init__(self, agent_key: str) -> None:
        self.agent_key = agent_key
        super().__init__(f"Agent '{agent_key}' not found or not published")


class EmbeddingError(Exception):
    def __init__(self, *, message: str, code: str | None, latency_ms: int) -> None:
        self.message, self.code, self.latency_ms = message, code, latency_ms
        super().__init__(message)
