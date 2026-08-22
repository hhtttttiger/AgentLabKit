"""RAGASEvalProvider 单元测试（mock RAGAS 依赖）。"""

from __future__ import annotations

import asyncio
import sys
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest

from evaluation.contracts import EvalCase, EvalRunConfig
from evaluation.providers.ragas_provider import RAGASEvalProvider


# ── 辅助 fixtures ────────────────────────────────────────────────────


@pytest.fixture
def sample_cases():
    return [
        EvalCase(
            id=1,
            input_text="什么是 RAG?",
            expected_output="RAG 是检索增强生成的缩写",
            context=["RAG (Retrieval-Augmented Generation) 是一种结合检索和生成的 AI 方法"],
        ),
        EvalCase(
            id=2,
            input_text="Python 的 GIL 是什么?",
            expected_output="GIL 是全局解释器锁",
            context=["GIL (Global Interpreter Lock) 是 CPython 的线程同步机制"],
        ),
    ]


@pytest.fixture
def sample_config():
    return EvalRunConfig(
        name="test-run",
        metric_configs=[{"name": "faithfulness"}, {"name": "answer_relevancy"}],
    )


def _make_ragas_module(evaluate_fn=None, dataset_cls=None):
    """构建 mock ragas 模块（含 metrics 子模块）。"""
    mod = ModuleType("ragas")
    mod.evaluate = evaluate_fn or MagicMock()
    mod.EvaluationDataset = dataset_cls or MagicMock()
    # ragas.metrics 子模块（Faithfulness, AnswerRelevancy 等）
    metrics_mod = ModuleType("ragas.metrics")
    metrics_mod.Faithfulness = MagicMock(return_value=MagicMock())
    metrics_mod.AnswerRelevancy = MagicMock(return_value=MagicMock())
    metrics_mod.ContextPrecision = MagicMock(return_value=MagicMock())
    mod.metrics = metrics_mod
    return mod


# ── RAGASEvalProvider 测试 ───────────────────────────────────────────


class TestRAGASEvalProvider:
    def test_list_metrics(self):
        provider = RAGASEvalProvider(llm=MagicMock())
        metrics = provider.list_metrics()
        assert "faithfulness" in metrics
        assert "answer_relevancy" in metrics
        assert "context_precision" in metrics

    def test_get_metric_known(self):
        provider = RAGASEvalProvider(llm=MagicMock())
        with patch.object(provider, "_resolve_ragas_metric") as mock_resolve:
            mock_resolve.return_value = MagicMock()
            metric = provider.get_metric("faithfulness")
            assert metric.name == "faithfulness"
            assert metric.provider == "ragas"

    def test_get_metric_unknown_raises(self):
        provider = RAGASEvalProvider(llm=MagicMock())
        with pytest.raises(KeyError, match="Unknown RAGAS metric"):
            provider.get_metric("nonexistent_metric")

    def test_custom_metrics_in_list(self):
        custom = MagicMock()
        custom.name = "my_metric"
        provider = RAGASEvalProvider(llm=MagicMock(), metrics={"my_metric": custom})
        metrics = provider.list_metrics()
        assert "my_metric" in metrics
        assert "faithfulness" in metrics  # 默认 metrics 仍在

    @pytest.mark.asyncio
    async def test_evaluate_success(self, sample_cases, sample_config):
        mock_llm = MagicMock()

        # Mock RAGAS evaluate 返回值 — per-case 数组
        mock_result = MagicMock()
        mock_result.get.side_effect = lambda name: {
            "faithfulness": [0.85, 0.80],
            "answer_relevancy": [0.92, 0.88],
        }.get(name)

        mock_eval_fn = MagicMock(return_value=mock_result)
        mock_ds_cls = MagicMock()
        mock_ds_cls.from_list.return_value = MagicMock()

        ragas_mod = _make_ragas_module(
            evaluate_fn=mock_eval_fn,
            dataset_cls=mock_ds_cls,
        )

        with patch.dict("sys.modules", {"ragas": ragas_mod}):
            provider = RAGASEvalProvider(llm=mock_llm)
            results = await provider.evaluate(
                sample_cases,
                ["faithfulness", "answer_relevancy"],
                sample_config,
            )

            # 返回 per-case 结果列表
            assert len(results) == 2
            for result in results:
                assert result.error_message is None
                assert len(result.metric_results) == 2
                assert result.overall_score > 0

            # 验证 RAGAS evaluate 被调用
            mock_eval_fn.assert_called_once()

    @pytest.mark.asyncio
    async def test_evaluate_no_ragas_installed(self, sample_cases, sample_config):
        """ragas 未安装时应返回错误而非崩溃。"""
        # 从 sys.modules 移除 ragas 以模拟未安装
        saved = sys.modules.pop("ragas", None)
        try:
            with patch.dict("sys.modules", {"ragas": None}):
                provider = RAGASEvalProvider(llm=MagicMock())
                results = await provider.evaluate(
                    sample_cases,
                    ["faithfulness"],
                    sample_config,
                )
                assert len(results) == 1
                assert results[0].error_message is not None
                assert "ragas" in results[0].error_message.lower()
        finally:
            if saved is not None:
                sys.modules["ragas"] = saved

    @pytest.mark.asyncio
    async def test_evaluate_empty_metrics(self, sample_cases, sample_config):
        """无有效 metric 时应返回错误。"""
        ragas_mod = _make_ragas_module()
        with patch.dict("sys.modules", {"ragas": ragas_mod}):
            provider = RAGASEvalProvider(llm=MagicMock())
            results = await provider.evaluate(sample_cases, [], sample_config)
            assert len(results) == 1
            assert results[0].error_message is not None

    @pytest.mark.asyncio
    async def test_evaluate_skips_unknown_metrics(self, sample_cases, sample_config):
        """未知 metric 应被跳过。"""
        mock_llm = MagicMock()
        mock_result = MagicMock()
        # 只有 faithfulness 有分数，未知 metric 返回 None
        mock_result.get.side_effect = lambda name: {
            "faithfulness": [0.8, 0.7],
        }.get(name)

        mock_eval_fn = MagicMock(return_value=mock_result)
        mock_ds_cls = MagicMock()
        mock_ds_cls.from_list.return_value = MagicMock()

        ragas_mod = _make_ragas_module(
            evaluate_fn=mock_eval_fn,
            dataset_cls=mock_ds_cls,
        )

        with patch.dict("sys.modules", {"ragas": ragas_mod}):
            provider = RAGASEvalProvider(llm=mock_llm)
            results = await provider.evaluate(
                sample_cases,
                ["faithfulness", "unknown_metric_xyz"],
                sample_config,
            )
            # 只有 faithfulness 被解析（unknown_metric_xyz 被跳过，结果中也没有其分数）
            assert len(results) == 2
            for result in results:
                assert len(result.metric_results) == 1
                assert result.metric_results[0].metric_name == "faithfulness"

    @pytest.mark.asyncio
    async def test_evaluate_ragas_exception(self, sample_cases, sample_config):
        """RAGAS evaluate() 抛异常时应返回错误结果。"""
        mock_eval_fn = MagicMock(side_effect=RuntimeError("RAGAS internal error"))
        mock_ds_cls = MagicMock()
        mock_ds_cls.from_list.return_value = MagicMock()

        ragas_mod = _make_ragas_module(
            evaluate_fn=mock_eval_fn,
            dataset_cls=mock_ds_cls,
        )

        with patch.dict("sys.modules", {"ragas": ragas_mod}):
            provider = RAGASEvalProvider(llm=MagicMock())
            results = await provider.evaluate(
                sample_cases,
                ["faithfulness"],
                sample_config,
            )
            assert len(results) == 1
            assert results[0].error_message is not None
            assert "RAGAS internal error" in results[0].error_message
