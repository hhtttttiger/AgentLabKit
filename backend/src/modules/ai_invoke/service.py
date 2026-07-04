"""Invoke service — agent and model invocation orchestration."""
from __future__ import annotations

import json
import time
import uuid
from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_runtime import AgentMessage, AgentRole
from agent_runtime import AgentTurnRequest as RuntimeTurnRequest
from modules.agent.models import AgentDefinition
from .agent_turn import run_agent_turn_stream, write_audit


class InvokeService:
    def __init__(
        self,
        *,
        gateway_service: Any,
        agent_runtime: Any,
        agent_definition_loader: Any,
        session_factory: Any,
    ) -> None:
        self._gateway = gateway_service
        self._runtime = agent_runtime
        self._loader = agent_definition_loader
        self._session_factory = session_factory

    # ── Agent options ──────────────────────────────────────────────────

    async def list_agent_options(self, db: AsyncSession) -> list[dict]:
        result = await db.execute(
            select(AgentDefinition)
            .where(
                AgentDefinition.is_enabled == True,
                AgentDefinition.published_version != None,
            )
            .order_by(AgentDefinition.display_name)
        )
        return [
            {
                "agentKey": a.agent_key,
                "displayName": a.display_name,
                "description": a.description,
                "icon": a.icon,
                "publishedVersionNumber": a.published_version,
            }
            for a in result.scalars().all()
        ]

    # ── Agent turn (sync) ──────────────────────────────────────────────

    async def run_agent_turn(
        self,
        *,
        agent_key: str,
        message: str,
        session_id: str | None,
        user_id: str,
        history: list[dict],
    ) -> dict:
        snapshot = await self._resolve_published_snapshot(agent_key)
        if snapshot is None:
            raise AgentNotFoundError(agent_key)

        agent_history = _history_to_messages(history)
        trace_id = str(uuid.uuid4())
        started_at = time.perf_counter()
        effective_session_id = session_id or str(uuid.uuid4())

        result = await self._runtime.run_turn(
            RuntimeTurnRequest(
                session_id=effective_session_id,
                user_message=message,
                history=agent_history,
                user_id=user_id,
                agent_key=agent_key,
                agent_version=snapshot.version_number,
                trace_id=trace_id,
            )
        )

        await write_audit(
            self._session_factory,
            agent_key=agent_key,
            run_id=trace_id,
            agent_version=snapshot.version_number,
            message=message,
            reply_text=result.reply_text,
            tool_events=list(result.tool_events),
            usage=result.usage,
            status="error" if result.error is not None else "success",
            duration_ms=int((time.perf_counter() - started_at) * 1000),
            error_message=result.error.message if result.error is not None else None,
        )

        return {
            "action": result.action.value if result.action else None,
            "replyText": result.reply_text,
            "handoffReason": result.handoff_reason,
            "agentKey": result.agent_key,
            "agentVersion": result.agent_version,
            "toolEvents": [te.model_dump() for te in result.tool_events],
            "usage": result.usage.model_dump() if result.usage else None,
            "error": result.error.model_dump() if result.error else None,
        }

    # ── Agent turn (stream) ────────────────────────────────────────────

    async def run_agent_turn_sse_stream(
        self,
        *,
        agent_key: str,
        message: str,
        session_id: str | None,
        user_id: str,
        history: list[dict],
    ) -> AsyncGenerator[str, None]:
        snapshot = await self._resolve_published_snapshot(agent_key)
        if snapshot is None:
            raise AgentNotFoundError(agent_key)

        agent_history = _history_to_messages(history)
        effective_session_id = session_id or str(uuid.uuid4())

        async for event in run_agent_turn_stream(
            self._runtime,
            agent_key=agent_key,
            agent_version=snapshot.version_number,
            message=message,
            session_id=effective_session_id,
            history=agent_history,
            session_factory=self._session_factory,
            user_id=user_id,
        ):
            yield event

    # ── Model text (sync) ──────────────────────────────────────────────

    async def generate_text(
        self,
        *,
        model_id: str,
        message: str,
        system_prompt: str | None = None,
    ) -> dict:
        from llm_gateway.models import TextGenerateRequest

        prompt = self._build_prompt(message, system_prompt)
        llm_request = TextGenerateRequest(model=model_id, prompt=prompt)
        result = await self._gateway.generate_text(llm_request)

        return {
            "content": result.text,
            "model": result.model,
            "provider": result.provider,
            "usage": result.usage.model_dump() if result.usage else None,
        }

    # ── Model text (stream) ────────────────────────────────────────────

    async def generate_text_sse_stream(
        self,
        *,
        model_id: str,
        message: str,
        system_prompt: str | None = None,
    ) -> AsyncGenerator[str, None]:
        from llm_gateway.models import TextGenerateRequest

        prompt = self._build_prompt(message, system_prompt)
        llm_request = TextGenerateRequest(model=model_id, prompt=prompt)

        try:
            async for event in self._gateway.generate_text_stream(llm_request):
                chunk = {
                    "content": event.delta or "",
                    "done": event.event_type == "finished",
                }
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            error_chunk = {"content": str(e), "done": True}
            yield f"data: {json.dumps(error_chunk, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"

    # ── Model text (test-stream with diagnostics) ──────────────────────

    async def generate_text_test_sse_stream(
        self,
        *,
        model_id: str,
        message: str,
        system_prompt: str | None = None,
    ) -> AsyncGenerator[str, None]:
        from llm_gateway.models import TextGenerateRequest

        prompt = self._build_prompt(message, system_prompt)
        llm_request = TextGenerateRequest(model=model_id, prompt=prompt)

        started_at = time.perf_counter()
        ttft_ms: int | None = None
        first_token_recorded = False
        instance_key: str | None = None
        provider_value: str | None = None
        model_value: str | None = None
        finish_reason: str | None = None
        usage = None

        try:
            async for event in self._gateway.generate_text_stream(llm_request):
                if event.instance_key:
                    instance_key = event.instance_key
                if event.provider is not None:
                    provider_value = event.provider.value
                if event.model:
                    model_value = event.model
                if event.usage:
                    usage = event.usage
                if event.finish_reason:
                    finish_reason = event.finish_reason
                if event.delta:
                    if not first_token_recorded:
                        ttft_ms = int((time.perf_counter() - started_at) * 1000)
                        first_token_recorded = True
                    chunk = {
                        "type": "content",
                        "content": event.delta,
                        "instance_key": instance_key,
                        "provider": provider_value,
                        "model": model_value,
                    }
                    yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"

            total_ms = int((time.perf_counter() - started_at) * 1000)
            stats = {
                "type": "stats",
                "ttft_ms": ttft_ms,
                "total_ms": total_ms,
                "instance_key": instance_key,
                "provider": provider_value,
                "model": model_value,
                "finish_reason": finish_reason,
                "input_tokens": usage.input_tokens if usage else None,
                "output_tokens": usage.output_tokens if usage else None,
                "total_tokens": usage.total_tokens if usage else None,
            }
            yield f"data: {json.dumps(stats, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            total_ms = int((time.perf_counter() - started_at) * 1000)
            error_payload = {
                "type": "error",
                "message": str(e),
                "code": getattr(getattr(e, "code", None), "value", None),
                "ttft_ms": ttft_ms,
                "total_ms": total_ms,
            }
            yield f"data: {json.dumps(error_payload, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"

    # ── Embedding test ─────────────────────────────────────────────────

    async def generate_embedding_test(
        self,
        *,
        model_id: str,
        text: str,
        dimensions: int | None = None,
    ) -> dict:
        from llm_gateway.models import EmbeddingGenerateRequest

        llm_request = EmbeddingGenerateRequest(
            model=model_id,
            input=text,
            dimensions=dimensions,
        )

        started_at = time.perf_counter()
        try:
            result = await self._gateway.generate_embedding(llm_request)
        except Exception as e:
            total_ms = int((time.perf_counter() - started_at) * 1000)
            raise EmbeddingError(
                message=str(e),
                code=getattr(getattr(e, "code", None), "value", None),
                latency_ms=total_ms,
            ) from e

        total_ms = int((time.perf_counter() - started_at) * 1000)
        embedding = result.embedding
        preview = embedding[:10] if len(embedding) > 10 else embedding

        return {
            "success": True,
            "provider": result.provider.value if result.provider else None,
            "model": result.model,
            "dimensions": result.dimensions,
            "vectorPreview": preview,
            "vectorPreviewTruncated": len(embedding) > 10,
            "usage": result.usage.model_dump() if result.usage else None,
            "latencyMs": total_ms,
        }

    # ── Helpers ────────────────────────────────────────────────────────

    async def _resolve_published_snapshot(self, agent_key: str):
        if self._loader is None:
            return None
        return await self._loader.load(agent_key)

    @staticmethod
    def _build_prompt(message: str, system_prompt: str | None) -> str:
        if system_prompt:
            return f"System: {system_prompt}\n\nUser: {message}"
        return message


# ── Domain errors ─────────────────────────────────────────────────────

class AgentNotFoundError(Exception):
    def __init__(self, agent_key: str) -> None:
        self.agent_key = agent_key
        super().__init__(f"Agent '{agent_key}' not found or not published")


class EmbeddingError(Exception):
    def __init__(self, *, message: str, code: str | None, latency_ms: int) -> None:
        self.message = message
        self.code = code
        self.latency_ms = latency_ms
        super().__init__(message)


# ── Shared helpers ─────────────────────────────────────────────────────

def _history_to_messages(items: list[dict]) -> list[AgentMessage]:
    return [
        AgentMessage(
            role=AgentRole(item["Role"].lower()),
            content=item["Content"],
            name=item.get("Name"),
            metadata=dict(item.get("Metadata") or {}),
        )
        for item in items
    ]
