"""AST-based static analysis tools for the Detector agent."""

from __future__ import annotations

import ast
from typing import Any

from agno.tools import tool

GOD_CLASS_MEMBER_THRESHOLD = 20
LONG_PARAMETER_THRESHOLD = 5
HIGH_COMPLEXITY_THRESHOLD = 10


def _calculate_cyclomatic_complexity(source_code: str) -> list[dict[str, Any]]:
    """Calculate cyclomatic complexity using radon library."""
    try:
        from radon.complexity import cc_visit
    except ImportError:
        return []

    try:
        complexity_blocks = cc_visit(source_code)
    except SyntaxError:
        return []


    results = []
    for block in complexity_blocks:
        results.append({
            "name": block.name,
            "complexity": block.complexity,
            "line": block.lineno,
            "endline": getattr(block, "endline", None),
            "type": block.__class__.__name__,
        })

    return results


def _find_god_classes(tree: ast.AST) -> list[dict[str, Any]]:
    """Find classes that might be 'god classes' - too many members."""
    god_classes = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            member_count = sum(1 for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Assign)))

            if member_count > GOD_CLASS_MEMBER_THRESHOLD:
                god_classes.append({
                    "name": node.name,
                    "line_start": node.lineno,
                    "line_end": getattr(node, "end_lineno", None),
                    "members": member_count,
                })

    return god_classes


def _find_long_parameter_functions(tree: ast.AST) -> list[dict[str, Any]]:
    """Find functions with too many parameters."""
    long_param_funcs = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            total_params = len(node.args.args) + len(node.args.kwonlyargs)

            if total_params >= LONG_PARAMETER_THRESHOLD:
                long_param_funcs.append({
                    "name": node.name,
                    "line_start": node.lineno,
                    "line_end": getattr(node, "end_lineno", None),
                    "params": total_params,
                })

    return long_param_funcs


def _identify_high_complexity_blocks(complexity_data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Filter out blocks with high cyclomatic complexity."""
    return [block for block in complexity_data if block["complexity"] > HIGH_COMPLEXITY_THRESHOLD]


def analyze_ast(source_code: str) -> dict[str, Any]:
    """Main analysis function - parses AST and runs various checks."""
    try:
        tree = ast.parse(source_code)
    except SyntaxError as exc:
        return {"error": f"Syntax error: {exc.msg}", "line": exc.lineno}

    complexity = _calculate_cyclomatic_complexity(source_code)

    results = {
        "complexity": complexity,
        "high_complexity_blocks": _identify_high_complexity_blocks(complexity),
        "god_classes": _find_god_classes(tree),
        "long_parameter_functions": _find_long_parameter_functions(tree),
    }

    return results


@tool(
    name="ast_analyzer_tool",
    description=(
        "Analisa código Python via AST + radon. Retorna métricas de complexidade ciclomática, "
        "God Classes (>20 membros), Long Parameter Lists (>=5 params) e blocos de alta complexidade."
    ),
)
def ast_analyzer_tool(source_code: str) -> dict[str, Any]:
    return analyze_ast(source_code)
