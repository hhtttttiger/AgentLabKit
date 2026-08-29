"""Evaluation CLI — 命令行接口。

支持：
- agentlab eval: 运行评估
- 配置文件 (eval.yaml)
- 阈值检查和退出码
- 基线比较
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path
from typing import Any

import yaml

from .compare import compare_runs, format_comparison_report
from .contracts_v2 import (
    DatasetExample,
    EvaluationContext,
    EvaluationResult,
    EvaluationRun,
    EvaluationRunStatus,
)
from .dataset import DatasetManager, DatasetEvaluationRunner, InMemoryDatasetStore
from .evaluators.agent_native import (
    MaxStepsEvaluator,
    NoErrorEvaluator,
    ToolCalledEvaluator,
    TrajectoryEvaluator,
)
from .replay import InMemoryRunStore, MockRunExecutor, ReplayRunner

logger = logging.getLogger(__name__)

# ── 配置文件 schema ────────────────────────────────────────────────


def load_config(config_path: str) -> dict[str, Any]:
    """加载 eval.yaml 配置文件。"""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"config file not found: {config_path}")

    with open(path) as f:
        config = yaml.safe_load(f)

    return config or {}


# ── 评估器工厂 ─────────────────────────────────────────────────────


EVALUATOR_MAP = {
    "tool_called": lambda cfg: ToolCalledEvaluator(tool_name=cfg.get("tool_name", "")),
    "max_steps": lambda cfg: MaxStepsEvaluator(max_steps=cfg.get("max_steps", 10)),
    "no_error": lambda cfg: NoErrorEvaluator(),
    "trajectory": lambda cfg: TrajectoryEvaluator(
        expected_trajectory=cfg.get("expected_trajectory", []),
    ),
}


def create_evaluators(config: dict[str, Any]) -> list:
    """从配置创建评估器列表。"""
    evaluators = []

    for metric_cfg in config.get("metrics", []):
        name = metric_cfg.get("name", "")
        factory = EVALUATOR_MAP.get(name)
        if factory:
            evaluators.append(factory(metric_cfg))
        else:
            logger.warning("unknown metric: %s", name)

    return evaluators


# ── 评估运行 ───────────────────────────────────────────────────────


async def run_evaluation(config: dict[str, Any]) -> EvaluationRun:
    """运行评估。"""
    # 创建存储
    store = InMemoryDatasetStore()
    manager = DatasetManager(store)

    # 加载数据集
    dataset_cfg = config.get("dataset", {})
    dataset_path = dataset_cfg.get("path", "")

    if dataset_path:
        # 从文件加载样本
        dataset_id = await manager.create_dataset("cli_dataset")
        examples = load_examples_from_file(dataset_path, dataset_id)
        await manager.add_examples(examples)
    else:
        dataset_id = await manager.create_dataset("cli_dataset")

    # 创建评估器
    evaluators = create_evaluators(config)
    if not evaluators:
        # 默认使用 no_error
        evaluators = [NoErrorEvaluator()]

    # 使用第一个评估器（或组合评估器）
    evaluator = evaluators[0] if evaluators else NoErrorEvaluator()

    # 运行评估
    runner = DatasetEvaluationRunner(evaluator, store)
    agent_key = config.get("agent_key", "default")

    return await runner.run(dataset_id, agent_key)


def load_examples_from_file(path: str, dataset_id: str = "cli_dataset") -> list[DatasetExample]:
    """从文件加载样本。"""
    import json

    with open(path) as f:
        data = json.load(f)

    examples = []
    for i, item in enumerate(data):
        examples.append(DatasetExample(
            example_id=str(i),
            dataset_id=dataset_id,
            input_text=item.get("input", ""),
            expected_output=item.get("expected_output"),
            context=item.get("context", []),
            tags=item.get("tags", []),
        ))

    return examples


# ── 退出码 ─────────────────────────────────────────────────────────


def check_threshold(
    result: EvaluationRun,
    threshold: float = 0.8,
    allow_failures: bool = False,
) -> int:
    """检查评估结果是否满足阈值。

    Returns:
        0: 通过
        1: 失败（低于阈值或有错误）
    """
    # 检查总体分数
    if result.overall_score < threshold:
        logger.error(
            "evaluation failed: score %.3f < threshold %.3f",
            result.overall_score,
            threshold,
        )
        return 1

    # 检查是否有失败的样本
    if not allow_failures and result.failed_examples > 0:
        logger.error(
            "evaluation failed: %d examples failed",
            result.failed_examples,
        )
        return 1

    return 0


# ── 基线比较 ───────────────────────────────────────────────────────


async def compare_with_baseline(
    current: EvaluationRun,
    baseline_path: str,
) -> int:
    """与基线比较。

    Returns:
        0: 没有回归
        1: 检测到回归
    """
    import json

    try:
        with open(baseline_path) as f:
            baseline_data = json.load(f)

        # 重建 baseline EvaluationRun
        baseline = EvaluationRun(
            run_id=baseline_data.get("run_id", "baseline"),
            dataset_id=baseline_data.get("dataset_id", ""),
            agent_key=baseline_data.get("agent_key", ""),
            status=EvaluationRunStatus(baseline_data.get("status", "completed")),
            overall_score=baseline_data.get("overall_score", 0.0),
            results=[
                EvaluationResult(
                    example_id=r["example_id"],
                    score=r.get("overall_score", 0.0),
                    message=r.get("error_message"),
                )
                for r in baseline_data.get("results", [])
            ],
        )

        # 比较
        comparison = compare_runs(baseline, current)

        # 检查是否有回归
        if comparison.regression_count > 0:
            logger.error(
                "regression detected: %d examples regressed",
                comparison.regression_count,
            )
            report = format_comparison_report(comparison)
            logger.error("\n%s", report)
            return 1

        return 0

    except FileNotFoundError:
        logger.warning("baseline file not found: %s", baseline_path)
        return 0


# ── 主入口 ─────────────────────────────────────────────────────────


async def main(config_path: str = "eval.yaml") -> int:
    """CLI 主入口。"""
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    try:
        # 加载配置
        config = load_config(config_path)

        # 运行评估
        result = await run_evaluation(config)

        # 输出结果
        print(f"\n{'='*60}")
        print(f"Evaluation Run: {result.run_id}")
        print(f"Status: {result.status.value}")
        print(f"Score: {result.overall_score:.3f}")
        print(f"Examples: {result.total_examples} total, {result.completed_examples} completed, {result.failed_examples} failed")
        print(f"{'='*60}\n")

        # 检查阈值
        threshold = config.get("threshold", 0.8)
        allow_failures = config.get("allow_failures", False)
        exit_code = check_threshold(result, threshold, allow_failures)

        # 基线比较
        baseline_path = config.get("baseline", "")
        if baseline_path and exit_code == 0:
            exit_code = await compare_with_baseline(result, baseline_path)

        # 保存结果
        output_path = config.get("output", "")
        if output_path:
            save_result(result, output_path)

        return exit_code

    except Exception as e:
        logger.exception("evaluation failed")
        print(f"\nError: {e}", file=sys.stderr)
        return 1


def save_result(result: EvaluationRun, path: str) -> None:
    """保存评估结果到文件。"""
    import json

    data = {
        "run_id": result.run_id,
        "dataset_id": result.dataset_id,
        "agent_key": result.agent_key,
        "status": result.status.value,
        "overall_score": result.overall_score,
        "total_examples": result.total_examples,
        "completed_examples": result.completed_examples,
        "failed_examples": result.failed_examples,
        "results": [
            {
                "example_id": r.example_id,
                "overall_score": r.overall_score,
                "error_message": r.error_message,
            }
            for r in result.results
        ],
    }

    with open(path, "w") as f:
        json.dump(data, f, indent=2)

    logger.info("result saved to %s", path)


# ── Click CLI (可选) ───────────────────────────────────────────────


try:
    import click

    @click.group()
    def cli():
        """AgentLabKit Evaluation CLI."""
        pass

    @cli.command()
    @click.option("--config", "-c", default="eval.yaml", help="Config file path")
    @click.option("--threshold", "-t", type=float, help="Score threshold")
    @click.option("--baseline", "-b", help="Baseline result file for comparison")
    @click.option("--output", "-o", help="Output result file")
    def eval(config: str, threshold: float | None, baseline: str | None, output: str | None):
        """Run evaluation."""
        # 加载并覆盖配置
        cfg = load_config(config)
        if threshold is not None:
            cfg["threshold"] = threshold
        if baseline:
            cfg["baseline"] = baseline
        if output:
            cfg["output"] = output

        # 运行
        exit_code = asyncio.run(main_from_config(cfg))
        sys.exit(exit_code)

    async def main_from_config(config: dict[str, Any]) -> int:
        """从配置运行评估。"""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        )

        try:
            result = await run_evaluation(config)

            print(f"\n{'='*60}")
            print(f"Evaluation Run: {result.run_id}")
            print(f"Status: {result.status.value}")
            print(f"Score: {result.overall_score:.3f}")
            print(f"Examples: {result.total_examples} total, {result.completed_examples} completed, {result.failed_examples} failed")
            print(f"{'='*60}\n")

            threshold = config.get("threshold", 0.8)
            allow_failures = config.get("allow_failures", False)
            exit_code = check_threshold(result, threshold, allow_failures)

            baseline_path = config.get("baseline", "")
            if baseline_path and exit_code == 0:
                exit_code = await compare_with_baseline(result, baseline_path)

            output_path = config.get("output", "")
            if output_path:
                save_result(result, output_path)

            return exit_code

        except Exception as e:
            logger.exception("evaluation failed")
            print(f"\nError: {e}", file=sys.stderr)
            return 1

except ImportError:
    # click 未安装，只提供 async main
    pass


__all__ = [
    "load_config",
    "create_evaluators",
    "run_evaluation",
    "check_threshold",
    "compare_with_baseline",
    "main",
    "save_result",
]
