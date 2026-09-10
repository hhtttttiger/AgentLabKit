"""Evaluation Evidence Composition — candidate execution evidence for metrics.

组合三份权威事实为 metric 可消费的 evidence：

- DatasetExample 拥有 input / expected(reference) / 稳定 example identity。
- AgentRun 拥有真实执行 identity 与 actual output（Runtime 是唯一创建者）。
- Trace projection 拥有这次 Run 真实发生了什么（retrieval attempts 等）。

核心不变量：candidate evaluation evidence MUST come from Candidate Run。
``DatasetExample.source_run_id`` 的 capture provenance 永远不会进入 evidence；
composer 只 carry 已有 identity，从不生成 run_id / trace_id / span_id。

Retrieval evidence 复用 Retrieval Observability v1 的既有事实
（retrieval.search spans 携带 bounded result refs），并保留 attempt 边界：
failed attempt + successful retry 不能被压扁成一个空数组。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Sequence


class EvidenceAvailability(str, Enum):
    """三类 evidence 可用性 —— 不能统一成 []。

    AVAILABLE      权威 evidence 存在（包括 retrieval 成功但 0 结果）。
    NOT_APPLICABLE 执行合法地没有该类 evidence（agent 根本没做 retrieval）。
    UNAVAILABLE    按语义应该存在，但权威 evidence 无法取得（如 trace 未投影）。
    """

    AVAILABLE = "available"
    NOT_APPLICABLE = "not_applicable"
    UNAVAILABLE = "unavailable"


# Machine-readable missing-evidence reasons（持久化到 metric entry 的 reason）。
REASON_TRACE_UNAVAILABLE = "trace_unavailable"
REASON_TRACE_FINALIZATION_TIMEOUT = "trace_finalization_timeout"
REASON_TRACE_INCOMPLETE = "trace_incomplete"
REASON_NO_RETRIEVAL = "no_retrieval_evidence"
REASON_RETRIEVAL_FAILED = "retrieval_failed"
REASON_MISSING_REFERENCE = "missing_reference"
REASON_MISSING_ACTUAL_OUTPUT = "missing_actual_output"
REASON_EVIDENCE_NOT_PROVIDED = "evidence_not_provided"


@dataclass(frozen=True, slots=True)
class RetrievalContextRef:
    """Bounded retrieval result ref —— 与 Runtime 的 RetrievalResultRef 对齐。"""

    knowledge_base_id: str | None = None
    document_id: str | None = None
    segment_id: str | None = None
    score: float | None = None
    title: str | None = None
    source: str | None = None
    content_preview: str | None = None


@dataclass(frozen=True, slots=True)
class RetrievalAttempt:
    """一次 retrieval 尝试 —— attempt 边界不可折叠。"""

    succeeded: bool
    query: str = ""
    result_count: int = 0
    refs: tuple[RetrievalContextRef, ...] = ()
    error_message: str | None = None


@dataclass(frozen=True, slots=True)
class RetrievalEvidence:
    """Candidate Trace 的 retrieval evidence。

    ``contexts`` 只包含 successful attempts 的 refs preview，按实际 execution
    order 组合（不按 score 排序、不混入 failed attempts）。
    """

    availability: EvidenceAvailability
    attempts: tuple[RetrievalAttempt, ...] = ()
    reason: str | None = None

    @property
    def successful_attempts(self) -> int:
        return sum(1 for attempt in self.attempts if attempt.succeeded)

    @property
    def contexts(self) -> tuple[str, ...]:
        """Successful attempts 的 bounded context previews（execution order）。"""
        return tuple(
            ref.content_preview
            for attempt in self.attempts
            if attempt.succeeded
            for ref in attempt.refs
            if ref.content_preview
        )


@dataclass(frozen=True, slots=True)
class EvaluationEvidence:
    """单个 example 的 canonical evaluation evidence。

    identity 字段（example_id/run_id/trace_id）只用于 truthfulness/debugging，
    metric provider 不得从它们推断事实。
    """

    example_id: str
    run_id: str | None
    trace_id: str | None
    input_text: str
    actual_output: str | None
    expected_output: str | None
    retrieval: RetrievalEvidence

    def retrieval_summary(self) -> dict[str, Any]:
        """Bounded summary for persistence/UI —— 不是 evidence 本身的副本。"""
        return {
            "availability": self.retrieval.availability.value,
            "attempts": len(self.retrieval.attempts),
            "successful_attempts": self.retrieval.successful_attempts,
            "contexts_used": len(self.retrieval.contexts),
            "reason": self.retrieval.reason,
        }


def compose_evaluation_evidence(
    *,
    example: Any,
    run: Any | None,
    spans: Sequence[Any] | None,
    trace_complete: bool | None = None,
    trace_unavailable_reason: str = REASON_TRACE_UNAVAILABLE,
) -> EvaluationEvidence:
    """纯函数：DatasetExample + Candidate AgentRun + spans → EvaluationEvidence。

    ``spans`` 是已从权威 Trace projection 读出的 span 摘要（SpanSummary 形状：
    name / kind / status / attributes）。composer 不查询数据库、不执行 agent、
    不推断 identity；``spans`` 为空表示 trace projection 不可取得（UNAVAILABLE），
    而不是"没有 retrieval"。

    ``trace_complete`` 是 projection 的 completeness truth（envelope 的
    dropped_span_count == 0）；None 表示调用方无法知晓，按 complete 处理 ——
    不完整时缺 evidence 绝不能被解释为"没有 retrieval"：

    - complete   + zero retrieval spans → NOT_APPLICABLE
    - incomplete + zero retrieval spans → UNAVAILABLE(trace_incomplete)
    - incomplete + retrieval spans      → AVAILABLE，summary 保留 incomplete
    """
    retrieval = _compose_retrieval_evidence(
        spans,
        trace_complete=trace_complete,
        trace_unavailable_reason=trace_unavailable_reason,
    )
    output = getattr(run, "output", None)
    return EvaluationEvidence(
        example_id=getattr(example, "example_id", ""),
        run_id=getattr(run, "run_id", None) if run is not None else None,
        trace_id=getattr(run, "trace_id", None) if run is not None else None,
        input_text=str(getattr(example, "input_text", "") or ""),
        actual_output=str(output) if output is not None else None,
        expected_output=getattr(example, "expected_output", None),
        retrieval=retrieval,
    )


def _compose_retrieval_evidence(
    spans: Sequence[Any] | None,
    *,
    trace_complete: bool | None = None,
    trace_unavailable_reason: str = REASON_TRACE_UNAVAILABLE,
) -> RetrievalEvidence:
    if not spans:
        # Trace projection 不可查询（包括尚未持久化的 race 窗口）：
        # 如实表达 UNAVAILABLE，禁止从 Run output / ToolResult 拼装 evidence。
        return RetrievalEvidence(
            availability=EvidenceAvailability.UNAVAILABLE,
            reason=trace_unavailable_reason,
        )

    attempts = tuple(
        _attempt_from_span(span)
        for span in spans
        if _is_retrieval_span(span)
    )
    if not attempts:
        if trace_complete is False:
            # Span projection 被截断且看不到 retrieval span：retrieval 可能
            # 确实发生过但 spans 被丢弃 —— "No retrieval occurred" 是 false
            # fact，必须如实 unavailable。
            return RetrievalEvidence(
                availability=EvidenceAvailability.UNAVAILABLE,
                reason=REASON_TRACE_INCOMPLETE,
            )
        # Trace 在、完整、但没有 retrieval span：agent 合法地没有做 retrieval。
        return RetrievalEvidence(
            availability=EvidenceAvailability.NOT_APPLICABLE,
        )
    return RetrievalEvidence(
        availability=EvidenceAvailability.AVAILABLE,
        attempts=attempts,
        # 已见的 retrieval evidence 仍可用，但 summary 必须保留 incomplete 状态。
        reason=REASON_TRACE_INCOMPLETE if trace_complete is False else None,
    )


def _is_retrieval_span(span: Any) -> bool:
    kind = str(getattr(span, "kind", "") or "").lower()
    if kind == "retrieval":
        return True
    return str(getattr(span, "name", "") or "").startswith("retrieval.")


def _attempt_from_span(span: Any) -> RetrievalAttempt:
    attributes: Mapping[str, Any] = getattr(span, "attributes", {}) or {}
    status = str(getattr(span, "status", "") or "").lower()
    error_message = (
        attributes.get("retrieval.error_message")
        or getattr(span, "error_message", None)
    )
    succeeded = status != "error" and not error_message
    return RetrievalAttempt(
        succeeded=succeeded,
        query=str(attributes.get("retrieval.query", "") or ""),
        result_count=int(attributes.get("retrieval.result_count", 0) or 0),
        refs=_refs_from_attributes(attributes),
        error_message=str(error_message) if error_message else None,
    )


def _refs_from_attributes(attributes: Mapping[str, Any]) -> tuple[RetrievalContextRef, ...]:
    raw_refs = attributes.get("retrieval.results")
    if isinstance(raw_refs, str):
        # OTel attribute 只支持原始序列；runtime 把 bounded refs 以 JSON 写入，
        # span processor 解码成数组，这里兜底容忍未解码的字符串。
        import json

        try:
            raw_refs = json.loads(raw_refs)
        except ValueError:
            return ()
    if not isinstance(raw_refs, Sequence) or isinstance(raw_refs, (str, bytes)):
        return ()
    refs = []
    for raw in raw_refs:
        if not isinstance(raw, Mapping):
            continue
        refs.append(RetrievalContextRef(
            knowledge_base_id=_optional_str(raw.get("knowledge_base_id")),
            document_id=_optional_str(raw.get("document_id")),
            segment_id=_optional_str(raw.get("segment_id")),
            score=_optional_float(raw.get("score")),
            title=_optional_str(raw.get("title")),
            source=_optional_str(raw.get("source")),
            content_preview=_optional_str(raw.get("content_preview")),
        ))
    return tuple(refs)


def _optional_str(value: Any) -> str | None:
    return str(value) if value not in (None, "") else None


def _optional_float(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


__all__ = [
    "EvidenceAvailability",
    "EvaluationEvidence",
    "RetrievalAttempt",
    "RetrievalContextRef",
    "RetrievalEvidence",
    "REASON_EVIDENCE_NOT_PROVIDED",
    "REASON_MISSING_ACTUAL_OUTPUT",
    "REASON_MISSING_REFERENCE",
    "REASON_NO_RETRIEVAL",
    "REASON_RETRIEVAL_FAILED",
    "REASON_TRACE_FINALIZATION_TIMEOUT",
    "REASON_TRACE_INCOMPLETE",
    "REASON_TRACE_UNAVAILABLE",
    "compose_evaluation_evidence",
]
