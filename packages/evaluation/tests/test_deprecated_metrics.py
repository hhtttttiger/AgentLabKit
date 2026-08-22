"""旧 Metric deprecated 警告测试。"""

from __future__ import annotations

import warnings

import pytest

from evaluation.metrics.base import (
    AnswerRelevanceMetric,
    FaithfulnessMetric,
    ContextRelevanceMetric,
)


class TestDeprecatedWarnings:
    def test_answer_relevance_deprecated(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            AnswerRelevanceMetric()
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "AnswerRelevanceMetric" in str(w[0].message)
            assert "RAGASEvalProvider" in str(w[0].message)

    def test_faithfulness_deprecated(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            FaithfulnessMetric()
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "FaithfulnessMetric" in str(w[0].message)

    def test_context_relevance_deprecated(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            ContextRelevanceMetric()
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "ContextRelevanceMetric" in str(w[0].message)

    def test_metrics_still_functional_after_deprecation(self):
        """deprecated metric 仍能正常评估（向后兼容）。"""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)

            metric = AnswerRelevanceMetric()
            assert metric.name == "answer_relevance"

    @pytest.mark.asyncio
    async def test_deprecated_metric_evaluate(self):
        """deprecated metric 的 evaluate 方法仍可调用。"""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)

            metric = FaithfulnessMetric()
            judge = type("MockJudge", (), {
                "score": lambda self, **kw: __import__("asyncio").ensure_future(
                    __import__("asyncio").sleep(0, result=(0.8, "good"))
                )
            })()

            # 无 context 时应返回 1.0
            result = await metric.evaluate(
                input_text="Q",
                actual_output="A",
                context=None,
                judge=None,
            )
            assert result.score == 1.0
