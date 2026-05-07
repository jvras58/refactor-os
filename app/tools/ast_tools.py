"""AST-based static analysis tools for the Detector agent."""
from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from agno.tools import tool


GOD_CLASS_MEMBER_THRESHOLD = 20
LONG_PARAMETER_THRESHOLD = 5
HIGH_COMPLEXITY_THRESHOLD = 10


@tool(
    name="read_source_code_tool",
    description="Lê um arquivo de código preservando numeração de linhas (1-based).",
)
def read_source_code_tool(file_path: str) -> dict[str, Any]:
    path = Path(file_path)
    if not path.is_file():
        return {"error": f"file not found: {file_path}"}
    text = path.read_text(encoding="utf-8")
    numbered = "\n".join(f"{i + 1:>4}: {line}" for i, line in enumerate(text.splitlines()))
    return {"file": str(path), "raw": text, "numbered": numbered, "line_count": text.count("\n") + 1}


def _cyclomatic_complexity(source_code: str) -> list[dict[str, Any]]:
    try:
        from radon.complexity import cc_visit
    except ImportError:  # pragma: no cover - radon listed as required dep
        return []
    try:
        blocks = cc_visit(source_code)
    except SyntaxError:
        return []
    return [
        {
            "name": b.name,
            "complexity": b.complexity,
            "line": b.lineno,
            "endline": getattr(b, "endline", None),
            "type": b.__class__.__name__,
        }
        for b in blocks
    ]


def _detect_god_classes(tree: ast.AST) -> list[dict[str, Any]]:
    god_classes = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            members = [n for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Assign))]
            if len(members) > GOD_CLASS_MEMBER_THRESHOLD:
                god_classes.append(
                    {
                        "name": node.name,
                        "line_start": node.lineno,
                        "line_end": getattr(node, "end_lineno", None),
                        "members": len(members),
                    }
                )
    return god_classes


def _detect_long_parameters(tree: ast.AST) -> list[dict[str, Any]]:
    found = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            param_count = len(node.args.args) + len(node.args.kwonlyargs)
            if param_count >= LONG_PARAMETER_THRESHOLD:
                found.append(
                    {
                        "name": node.name,
                        "line_start": node.lineno,
                        "line_end": getattr(node, "end_lineno", None),
                        "params": param_count,
                    }
                )
    return found


def _detect_complex_branches(complexity: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [c for c in complexity if c["complexity"] > HIGH_COMPLEXITY_THRESHOLD]


def analyze_ast(source_code: str) -> dict[str, Any]:
    """Pure analysis function (no agent decorator) — used by tests and the tool wrapper."""
    try:
        tree = ast.parse(source_code)
    except SyntaxError as exc:
        return {"error": f"syntax error: {exc.msg}", "line": exc.lineno}

    complexity = _cyclomatic_complexity(source_code)
    return {
        "complexity": complexity,
        "high_complexity_blocks": _detect_complex_branches(complexity),
        "god_classes": _detect_god_classes(tree),
        "long_parameter_functions": _detect_long_parameters(tree),
    }


@tool(
    name="ast_analyzer_tool",
    description=(
        "Analisa código Python via AST + radon. Retorna métricas de complexidade ciclomática, "
        "God Classes (>20 membros), Long Parameter Lists (>=5 params) e blocos de alta complexidade."
    ),
)
def ast_analyzer_tool(source_code: str) -> dict[str, Any]:
    return analyze_ast(source_code)
