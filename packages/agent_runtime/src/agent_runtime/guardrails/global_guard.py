"""Global guardrail service — matching, audit, and response building.

All global guardrail logic extracted from ``runtime/engine.py`` so that the
engine stays focused on the generic turn lifecycle.

Future integration path (TODO):
    The ``Guard`` protocol currently supports only PASS / MODIFY / BLOCK
    verdicts but global guardrails also need an "alert" (annotate-only)
    action.  Once the ``GuardVerdict`` enum gains an ``ALERT`` member
    (or ``GuardResult`` gains a generic ``metadata`` carry-field), each
    ``GlobalGuardrailRule`` can be wrapped as a ``GlobalGuardrailGuard``
    instance that implements ``Guard`` and is appended to the standard
    ``GuardsPipeline.input_guards`` / ``output_guards`` lists.  That will
    let us remove the parallel evaluation in the engine entirely.
"""

from __future__ import annotations

import logging
import re
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Literal

from ..contracts.models import (
    AgentAction,
    AgentMessage,
    AgentRole,
    AppliedSkillRecord,
    AgentTurnRequest,
    AgentTurnResult,
    AgentTurnStreamEvent,
    HandoffTarget,
)
from ..guardrails import GuardResult, GlobalGuardrailRule, GlobalGuardrailsSnapshot, GuardsPipeline

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

GLOBAL_GUARDRAIL_LITERAL_MATCHER_TYPES = frozenset({"hint", "literal", "keyword"})
GLOBAL_GUARDRAIL_SEMANTIC_MATCHER_TYPES = frozenset({"llm_judge", "semantic", "rubric"})
GLOBAL_GUARDRAIL_STOPWORDS = frozenset(
    {
        "a", "an", "and", "assistant", "content", "data", "detect",
        "disclosure", "disclosures", "the", "this", "that", "to", "or",
        "of", "for", "in", "on", "with", "when", "share", "request",
        "requested", "asked", "output", "response", "reply", "match",
    }
)
GLOBAL_GUARDRAIL_CONCEPT_SYNONYMS: dict[str, tuple[str, ...]] = {
    "pci": ("credit card", "card number", "payment card", "cvv", "银行卡号"),
    "payment": ("credit card", "card number", "payment card", "银行卡号"),
    "card": ("credit card", "card number", "payment card", "银行卡号"),
    "credentials": ("password", "passcode", "api key", "token", "secret"),
    "credential": ("password", "passcode", "api key", "token", "secret"),
    "password": ("password", "passcode", "secret"),
    "secret": ("secret", "api key", "token", "credential"),
    "pii": ("email", "phone", "ssn", "social security", "passport"),
    "privacy": ("email", "phone", "ssn", "social security", "passport"),
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class GlobalGuardrailMatch:
    revision: int
    stage: Literal["input", "output"]
    rule: GlobalGuardrailRule
    reason: str | None = None
    confidence: float | None = None


@dataclass(slots=True)
class GlobalGuardrailMatcherResult:
    matched: bool
    confidence: float | None = None
    reason: str | None = None


@dataclass(slots=True)
class GlobalGuardrailAuditRecord:
    session_id: str
    trace_id: str
    revision: int
    stage: str
    rule_key: str
    scope: str
    action: str
    reason: str | None
    priority: int
    confidence: float | None = None


# ---------------------------------------------------------------------------
# GlobalGuardrailService
# ---------------------------------------------------------------------------


class GlobalGuardrailService:
    """Manages global guardrail evaluation, audit, and response building.

    Extracted from ``AgentRuntime`` to decouple global guardrail logic from
    the core turn lifecycle.
    """

    def __init__(
        self,
        *,
        get_snapshot: Callable[[], GlobalGuardrailsSnapshot | None],
        get_block_text: Callable[[], str],
        get_handoff_message: Callable[[], str],
    ) -> None:
        self._get_snapshot = get_snapshot
        self._get_block_text = get_block_text
        self._get_handoff_message = get_handoff_message
        self._records: deque[GlobalGuardrailAuditRecord] = deque(maxlen=100)

    # ------------------------------------------------------------------
    # Public query API (delegated from AgentRuntime)
    # ------------------------------------------------------------------

    def recent_samples(self, limit: int = 10) -> list[dict[str, object]]:
        if limit <= 0:
            return []
        records = list(self._records)[-limit:]
        return [
            {
                "session_id": record.session_id,
                "trace_id": record.trace_id,
                "revision": record.revision,
                "stage": record.stage,
                "rule_key": record.rule_key,
                "scope": record.scope,
                "action": record.action,
                "reason": record.reason,
                "priority": record.priority,
                "confidence": record.confidence,
            }
            for record in reversed(records)
        ]

    # ------------------------------------------------------------------
    # Core evaluation
    # ------------------------------------------------------------------

    async def evaluate(
        self,
        *,
        request: AgentTurnRequest,
        stage: Literal["input", "output"],
        content: str,
    ) -> GlobalGuardrailMatch | None:
        snapshot = self._get_snapshot()
        if snapshot is None:
            return None

        candidate_rules = sorted(
            (
                rule
                for rule in snapshot.rules
                if rule.enabled and _scope_matches_stage(rule.matcher.scope, stage)
            ),
            key=lambda r: r.priority,
        )
        for rule in candidate_rules:
            match = await self._match_rule(
                rule=rule, request=request, stage=stage, content=content,
                snapshot_revision=snapshot.revision,
            )
            if match is not None:
                return match
        return None

    async def _match_rule(
        self,
        *,
        rule: GlobalGuardrailRule,
        request: AgentTurnRequest,
        stage: Literal["input", "output"],
        content: str,
        snapshot_revision: int,
    ) -> GlobalGuardrailMatch | None:
        if not content.strip():
            return None

        try:
            match_result = self._default_matcher(rule=rule, content=content)
        except Exception:
            logger.exception(
                "global_guardrail_matcher_failed trace_id=%s session_id=%s rule_key=%s failure_mode=%s",
                request.trace_id, request.session_id, rule.rule_key, rule.failure_mode,
            )
            if rule.failure_mode.strip().lower() != "fail_closed":
                return None
            match_result = GlobalGuardrailMatcherResult(
                matched=True, confidence=_threshold(rule),
            )

        if match_result is None or not match_result.matched:
            return None

        confidence = match_result.confidence
        if confidence is not None and confidence < _threshold(rule):
            return None

        reason = match_result.reason or _resolve_reason(rule)
        return GlobalGuardrailMatch(
            revision=snapshot_revision,
            stage=stage,
            rule=rule,
            reason=reason,
            confidence=confidence if confidence is not None else 1.0,
        )

    def _default_matcher(
        self,
        *,
        rule: GlobalGuardrailRule,
        content: str,
    ) -> GlobalGuardrailMatcherResult:
        matcher_type = _normalize_matcher_type(rule.matcher.type)
        if matcher_type in GLOBAL_GUARDRAIL_LITERAL_MATCHER_TYPES:
            return _match_hints(rule, content)
        if matcher_type in GLOBAL_GUARDRAIL_SEMANTIC_MATCHER_TYPES:
            return _match_semantically(rule, content)
        return _match_hints(rule, content)

    # ------------------------------------------------------------------
    # Audit
    # ------------------------------------------------------------------

    def record_match(
        self,
        *,
        request: AgentTurnRequest,
        match: GlobalGuardrailMatch,
    ) -> None:
        self._records.append(
            GlobalGuardrailAuditRecord(
                session_id=request.session_id,
                trace_id=request.trace_id or "",
                revision=match.revision,
                stage=match.stage,
                rule_key=match.rule.rule_key,
                scope=match.rule.matcher.scope,
                action=match.rule.action,
                reason=match.reason,
                priority=match.rule.priority,
                confidence=match.confidence,
            )
        )

    @staticmethod
    def build_metadata(match: GlobalGuardrailMatch) -> dict[str, str]:
        metadata = {
            "global_guardrail_action": match.rule.action,
            "global_guardrail_rule_key": match.rule.rule_key,
            "global_guardrail_scope": match.rule.matcher.scope,
            "global_guardrail_stage": match.stage,
            "global_guardrails_revision": str(match.revision),
        }
        if match.reason:
            metadata["global_guardrail_reason"] = match.reason
        if match.confidence is not None:
            metadata["global_guardrail_confidence"] = f"{match.confidence:.3f}"
        return metadata

    @staticmethod
    def annotate_terminal_assistant_message(
        raw_messages: list[AgentMessage],
        *,
        reply_text: str,
        metadata: dict[str, str],
    ) -> list[AgentMessage]:
        normalized = [message.model_copy(deep=True) for message in raw_messages]
        for index in range(len(normalized) - 1, -1, -1):
            if normalized[index].role is AgentRole.ASSISTANT:
                merged_metadata = dict(normalized[index].metadata)
                merged_metadata.update(metadata)
                normalized[index] = normalized[index].model_copy(
                    update={"metadata": merged_metadata}
                )
                return normalized
        normalized.append(
            AgentMessage(role=AgentRole.ASSISTANT, content=reply_text, metadata=dict(metadata))
        )
        return normalized

    # ------------------------------------------------------------------
    # Response builders — blocking
    # ------------------------------------------------------------------

    def blocked_response(
        self,
        *,
        request: AgentTurnRequest,
        definition: Any,
        match: GlobalGuardrailMatch,
        applied_skills: list[AppliedSkillRecord] | None = None,
    ) -> AgentTurnResult:
        block_text = self._get_block_text()
        return AgentTurnResult(
            session_id=request.session_id,
            trace_id=request.trace_id or "",
            action=AgentAction.REPLY,
            reply_text=block_text,
            raw_messages=[
                AgentMessage(
                    role=AgentRole.ASSISTANT,
                    content=block_text,
                    metadata=self.build_metadata(match),
                )
            ],
            agent_key=request.agent_key,
            agent_version=definition.version_number if definition else None,
            applied_skills=list(applied_skills or []),
        )

    def handoff_response(
        self,
        *,
        request: AgentTurnRequest,
        definition: Any,
        match: GlobalGuardrailMatch,
        applied_skills: list[AppliedSkillRecord] | None = None,
    ) -> AgentTurnResult:
        handoff_text = self._get_handoff_message()
        reason = match.reason or f"global_guardrail:{match.rule.rule_key}"
        return AgentTurnResult(
            session_id=request.session_id,
            trace_id=request.trace_id or "",
            action=AgentAction.HANDOFF_HUMAN,
            reply_text=handoff_text,
            handoff_reason=reason,
            raw_messages=[
                AgentMessage(
                    role=AgentRole.ASSISTANT,
                    content=handoff_text,
                    metadata=self.build_metadata(match),
                )
            ],
            agent_key=request.agent_key,
            agent_version=definition.version_number if definition else None,
            applied_skills=list(applied_skills or []),
            handoff_target=HandoffTarget(target_type="human", reason=reason),
        )

    # ------------------------------------------------------------------
    # Response builders — streaming
    # ------------------------------------------------------------------

    def blocked_stream_event(
        self,
        *,
        request: AgentTurnRequest,
        definition: Any,
        match: GlobalGuardrailMatch,
        usage: Any | None = None,
        applied_skills: list[AppliedSkillRecord] | None = None,
    ) -> AgentTurnStreamEvent:
        block_text = self._get_block_text()
        return AgentTurnStreamEvent(
            event_type="reply_completed",
            session_id=request.session_id,
            trace_id=request.trace_id or "",
            reply_text=block_text,
            usage=usage,
            raw_messages=[
                AgentMessage(
                    role=AgentRole.ASSISTANT,
                    content=block_text,
                    metadata=self.build_metadata(match),
                )
            ],
            applied_skills=list(applied_skills or []),
            agent_key=request.agent_key,
            agent_version=definition.version_number if definition else None,
        )

    def handoff_stream_event(
        self,
        *,
        request: AgentTurnRequest,
        definition: Any,
        match: GlobalGuardrailMatch,
        handoff_text: str,
        usage: Any | None = None,
        applied_skills: list[AppliedSkillRecord] | None = None,
    ) -> AgentTurnStreamEvent:
        reason = match.reason or f"global_guardrail:{match.rule.rule_key}"
        return AgentTurnStreamEvent(
            event_type="handoff",
            session_id=request.session_id,
            trace_id=request.trace_id or "",
            reply_text=handoff_text,
            handoff_reason=reason,
            usage=usage,
            raw_messages=[
                AgentMessage(
                    role=AgentRole.ASSISTANT,
                    content=handoff_text,
                    metadata=self.build_metadata(match),
                )
            ],
            applied_skills=list(applied_skills or []),
            agent_key=request.agent_key,
            agent_version=definition.version_number if definition else None,
            handoff_target=HandoffTarget(target_type="human", reason=reason),
        )


# ---------------------------------------------------------------------------
# Module-level helpers (pure functions)
# ---------------------------------------------------------------------------


def _normalize_matcher_type(value: str) -> str:
    return value.strip().lower() if value else "literal"


def _threshold(rule: GlobalGuardrailRule) -> float:
    if rule.matcher.threshold is not None:
        return max(0.0, min(1.0, rule.matcher.threshold))
    matcher_type = _normalize_matcher_type(rule.matcher.type)
    if matcher_type in GLOBAL_GUARDRAIL_LITERAL_MATCHER_TYPES:
        return 1.0
    return 0.5


def _match_hints(rule: GlobalGuardrailRule, content: str) -> GlobalGuardrailMatcherResult:
    haystack = content.casefold()
    matched_hint = next(
        (
            hint.strip()
            for hint in rule.matcher.hints
            if hint.strip() and hint.casefold() in haystack
        ),
        None,
    )
    return GlobalGuardrailMatcherResult(
        matched=matched_hint is not None,
        confidence=1.0 if matched_hint is not None else 0.0,
        reason=None,
    )


def _match_semantically(rule: GlobalGuardrailRule, content: str) -> GlobalGuardrailMatcherResult:
    haystack = content.casefold()
    phrases = {
        hint.strip().casefold()
        for hint in rule.matcher.hints
        if hint.strip()
    }
    concept_text = " ".join(
        part.strip()
        for part in (rule.matcher.rubric, rule.title, rule.description)
        if part and part.strip()
    ).casefold()
    for concept, synonyms in GLOBAL_GUARDRAIL_CONCEPT_SYNONYMS.items():
        if concept in concept_text:
            phrases.update(synonyms)

    matched_phrase = next((phrase for phrase in phrases if phrase and phrase in haystack), None)
    if matched_phrase is not None:
        return GlobalGuardrailMatcherResult(matched=True, confidence=1.0)

    rubric_tokens = {
        token
        for token in re.findall(r"[a-z0-9]+", concept_text)
        if token not in GLOBAL_GUARDRAIL_STOPWORDS
    }
    content_tokens = set(re.findall(r"[a-z0-9]+", haystack))
    if rubric_tokens:
        overlap = len(rubric_tokens & content_tokens) / len(rubric_tokens)
        if overlap > 0:
            return GlobalGuardrailMatcherResult(matched=True, confidence=overlap)

    return GlobalGuardrailMatcherResult(matched=False, confidence=0.0)


def _scope_matches_stage(scope: str, stage: Literal["input", "output"]) -> bool:
    normalized = scope.strip().lower()
    if normalized in {"input", "request", "user_input"}:
        return stage == "input"
    if normalized in {"output", "response", "assistant_output"}:
        return stage == "output"
    if normalized in {"all", "*", "both", "turn", "conversation", "input_output"}:
        return True
    return False


def _resolve_reason(rule: GlobalGuardrailRule) -> str | None:
    for key in ("reason", "handoff_reason", "handoffReason", "alert_reason", "alertReason"):
        value = rule.action_config.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return f"global_guardrail:{rule.rule_key}"
