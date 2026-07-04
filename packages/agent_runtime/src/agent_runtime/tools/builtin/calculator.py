"""Built-in calculator tool.

Evaluates safe arithmetic expressions.  Supports the four basic operators,
parentheses, and the ``**`` exponentiation operator.  No arbitrary code
execution — expressions are parsed with the ``ast`` module and only numeric
literals and safe operators are allowed.
"""

from __future__ import annotations

import ast
import math
import operator
from typing import Any

from ..contracts import ToolExecutionContext, ToolResult, ToolSpec


_SPEC = ToolSpec(
    name="calculator",
    description=(
        "Evaluate a safe arithmetic expression and return the numeric result. "
        "Supports +, -, *, /, //, %, ** and parentheses. "
        "Example: '(12 + 8) * 3 / 2' → '30.0'."
    ),
    parameters_schema={
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "The arithmetic expression to evaluate.",
                "minLength": 1,
            },
        },
        "required": ["expression"],
        "additionalProperties": False,
    },
    returns_description="The numeric result as a string.",
    tags=frozenset({"utility", "math", "read_only"}),
    timeout_seconds=2.0,
    max_retries=0,
    is_idempotent=True,
)

# ---------------------------------------------------------------------------
# Allowed AST node types — only numeric literals and safe binary/unary ops
# ---------------------------------------------------------------------------

_SAFE_NODES = frozenset(
    {
        ast.Expression,
        ast.BinOp,
        ast.UnaryOp,
        ast.Constant,
        ast.Add,
        ast.Sub,
        ast.Mult,
        ast.Div,
        ast.FloorDiv,
        ast.Mod,
        ast.Pow,
        ast.UAdd,
        ast.USub,
    }
)

_BINARY_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

_UNARY_OPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def _safe_eval(node: ast.AST) -> float:
    """Recursively evaluate a safe AST node."""
    if not isinstance(node, tuple(_SAFE_NODES)):
        raise ValueError(f"Unsafe expression node: {type(node).__name__}")

    if isinstance(node, ast.Expression):
        return _safe_eval(node.body)

    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return float(node.value)
        raise ValueError(f"Non-numeric constant: {node.value!r}")

    if isinstance(node, ast.BinOp):
        op_fn = _BINARY_OPS.get(type(node.op))
        if op_fn is None:
            raise ValueError(f"Unsupported binary op: {type(node.op).__name__}")
        left = _safe_eval(node.left)
        right = _safe_eval(node.right)
        if isinstance(node.op, ast.Div) and right == 0:
            raise ZeroDivisionError("division by zero")
        if isinstance(node.op, ast.Pow) and abs(left) > 1e6 and abs(right) > 6:
            raise ValueError("Exponentiation result would be too large")
        return op_fn(left, right)

    if isinstance(node, ast.UnaryOp):
        op_fn = _UNARY_OPS.get(type(node.op))
        if op_fn is None:
            raise ValueError(f"Unsupported unary op: {type(node.op).__name__}")
        return op_fn(_safe_eval(node.operand))

    raise ValueError(f"Unhandled node type: {type(node).__name__}")


class CalculatorTool:
    """Safe arithmetic expression evaluator.

    No constructor arguments needed — the tool is fully stateless.
    """

    spec: ToolSpec = _SPEC

    async def execute(
        self,
        arguments: dict[str, Any],
        context: ToolExecutionContext,
    ) -> ToolResult:
        expression: str = str(arguments.get("expression", "")).strip()
        if not expression:
            return ToolResult(
                output="",
                status="error",
                error_message="'expression' must not be empty.",
            )

        try:
            tree = ast.parse(expression, mode="eval")
            result = _safe_eval(tree)
        except ZeroDivisionError:
            return ToolResult(
                output="Error: division by zero",
                status="error",
                error_message="division by zero",
            )
        except (ValueError, SyntaxError) as exc:
            return ToolResult(
                output=f"Error: {exc}",
                status="error",
                error_message=str(exc),
            )

        # Format: prefer integer display when the result is a whole number
        if math.isfinite(result) and result == int(result):
            output = str(int(result))
        else:
            output = str(result)

        return ToolResult(
            output=output,
            structured_data={"result": result},
            status="success",
        )
