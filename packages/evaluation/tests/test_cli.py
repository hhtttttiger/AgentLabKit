"""Tests for Evaluation CLI."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from evaluation.cli import (
    check_threshold,
    create_evaluators,
    load_config,
    load_examples_from_file,
    run_evaluation,
    save_result,
)
from evaluation.contracts_v2 import (
    EvaluationResult,
    EvaluationRun,
    EvaluationRunStatus,
)


def _make_run(
    overall_score: float = 0.9,
    failed_examples: int = 0,
    total_examples: int = 5,
) -> EvaluationRun:
    return EvaluationRun(
        run_id="test-run",
        dataset_id="test-dataset",
        agent_key="test-agent",
        status=EvaluationRunStatus.COMPLETED if failed_examples == 0 else EvaluationRunStatus.FAILED,
        results=[
            EvaluationResult(example_id=str(i), score=overall_score)
            for i in range(total_examples)
        ],
        total_examples=total_examples,
        completed_examples=total_examples - failed_examples,
        failed_examples=failed_examples,
        overall_score=overall_score,
    )


# ── load_config ────────────────────────────────────────────────────


class TestLoadConfig:
    def test_load_valid_config(self, tmp_path):
        config_path = tmp_path / "eval.yaml"
        config_path.write_text("""
dataset:
  path: examples.json
metrics:
  - name: no_error
threshold: 0.8
""")
        config = load_config(str(config_path))
        assert config["threshold"] == 0.8
        assert config["dataset"]["path"] == "examples.json"

    def test_load_missing_file(self):
        with pytest.raises(FileNotFoundError):
            load_config("nonexistent.yaml")

    def test_load_empty_config(self, tmp_path):
        config_path = tmp_path / "eval.yaml"
        config_path.write_text("")
        config = load_config(str(config_path))
        assert config == {}


# ── create_evaluators ──────────────────────────────────────────────


class TestCreateEvaluators:
    def test_create_no_error_evaluator(self):
        config = {
            "metrics": [{"name": "no_error"}],
        }
        evaluators = create_evaluators(config)
        assert len(evaluators) == 1
        assert evaluators[0].name == "no_error"

    def test_create_multiple_evaluators(self):
        config = {
            "metrics": [
                {"name": "no_error"},
                {"name": "max_steps", "max_steps": 5},
            ],
        }
        evaluators = create_evaluators(config)
        assert len(evaluators) == 2

    def test_create_unknown_evaluator(self):
        config = {
            "metrics": [{"name": "unknown"}],
        }
        evaluators = create_evaluators(config)
        assert len(evaluators) == 0

    def test_create_empty_metrics(self):
        config = {"metrics": []}
        evaluators = create_evaluators(config)
        assert len(evaluators) == 0


# ── check_threshold ────────────────────────────────────────────────


class TestCheckThreshold:
    def test_pass_above_threshold(self):
        run = _make_run(overall_score=0.9)
        assert check_threshold(run, threshold=0.8) == 0

    def test_fail_below_threshold(self):
        run = _make_run(overall_score=0.7)
        assert check_threshold(run, threshold=0.8) == 1

    def test_fail_with_errors(self):
        run = _make_run(overall_score=0.9, failed_examples=1)
        assert check_threshold(run, threshold=0.8, allow_failures=False) == 1

    def test_pass_with_errors_allowed(self):
        run = _make_run(overall_score=0.9, failed_examples=1)
        assert check_threshold(run, threshold=0.8, allow_failures=True) == 0

    def test_exact_threshold(self):
        run = _make_run(overall_score=0.8)
        assert check_threshold(run, threshold=0.8) == 0


# ── load_examples_from_file ────────────────────────────────────────


class TestLoadExamples:
    def test_load_valid_examples(self, tmp_path):
        examples_path = tmp_path / "examples.json"
        examples_path.write_text(json.dumps([
            {"input": "What is AI?", "expected_output": "AI is..."},
            {"input": "What is ML?", "expected_output": "ML is...", "tags": ["ml"]},
        ]))

        examples = load_examples_from_file(str(examples_path))
        assert len(examples) == 2
        assert examples[0].input_text == "What is AI?"
        assert examples[1].tags == ["ml"]

    def test_load_missing_file(self):
        with pytest.raises(FileNotFoundError):
            load_examples_from_file("nonexistent.json")


# ── save_result ────────────────────────────────────────────────────


class TestSaveResult:
    def test_save_result(self, tmp_path):
        run = _make_run(overall_score=0.9)
        output_path = str(tmp_path / "result.json")

        save_result(run, output_path)

        with open(output_path) as f:
            data = json.load(f)

        assert data["run_id"] == "test-run"
        assert data["overall_score"] == 0.9
        assert len(data["results"]) == 5


# ── run_evaluation ─────────────────────────────────────────────────


class TestRunEvaluation:
    @pytest.mark.asyncio
    async def test_run_with_examples_file(self, tmp_path):
        examples_path = tmp_path / "examples.json"
        examples_path.write_text(json.dumps([
            {"input": "What is AI?"},
            {"input": "What is ML?"},
        ]))

        config = {
            "dataset": {"path": str(examples_path)},
            "metrics": [{"name": "no_error"}],
            "agent_key": "test-agent",
        }

        result = await run_evaluation(config)

        assert result.total_examples == 2
        assert result.status in (EvaluationRunStatus.COMPLETED, EvaluationRunStatus.FAILED)

    @pytest.mark.asyncio
    async def test_run_with_default_evaluator(self):
        config = {
            "agent_key": "test-agent",
        }

        result = await run_evaluation(config)

        # 空数据集
        assert result.status == EvaluationRunStatus.FAILED
        assert result.error_message == "dataset is empty"


# ── compare_with_baseline ──────────────────────────────────────────


class TestCompareWithBaseline:
    @pytest.mark.asyncio
    async def test_no_regression(self, tmp_path):
        baseline_path = tmp_path / "baseline.json"
        baseline_path.write_text(json.dumps({
            "run_id": "baseline",
            "dataset_id": "test",
            "agent_key": "test",
            "status": "completed",
            "overall_score": 0.8,
            "results": [
                {"example_id": "0", "overall_score": 0.8},
                {"example_id": "1", "overall_score": 0.8},
            ],
        }))

        current = _make_run(overall_score=0.9)

        from evaluation.cli import compare_with_baseline
        exit_code = await compare_with_baseline(current, str(baseline_path))
        assert exit_code == 0

    @pytest.mark.asyncio
    async def test_with_regression(self, tmp_path):
        baseline_path = tmp_path / "baseline.json"
        baseline_path.write_text(json.dumps({
            "run_id": "baseline",
            "dataset_id": "test",
            "agent_key": "test",
            "status": "completed",
            "overall_score": 0.9,
            "results": [
                {"example_id": "0", "overall_score": 0.9},
                {"example_id": "1", "overall_score": 0.9},
            ],
        }))

        current = _make_run(overall_score=0.7)

        from evaluation.cli import compare_with_baseline
        exit_code = await compare_with_baseline(current, str(baseline_path))
        assert exit_code == 1

    @pytest.mark.asyncio
    async def test_missing_baseline(self):
        current = _make_run()

        from evaluation.cli import compare_with_baseline
        exit_code = await compare_with_baseline(current, "nonexistent.json")
        assert exit_code == 0  # 不阻塞
