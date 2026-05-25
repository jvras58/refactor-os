"""Deterministic quality checks used to score the Recommender's output offline.

These are static heuristics (no LLM): a refactoring is judged on three objective axes
— pattern correctness, syntax validity and public-API preservation. They are intentionally
conservative so the Refactorador metric reflects measurable facts, not opinion.
"""
from __future__ import annotations

import ast
from typing import Any

from app.core.schemas import DesignPatternType
from app.tools.syntax_tools import check_syntax


def pattern_matches(applied: DesignPatternType, expected: DesignPatternType) -> bool:
    """True when the applied pattern equals the expected pattern for the smell."""
    return applied == expected


def extract_public_api(source_code: str) -> set[str]:
    """Top-level public functions/classes and public methods (names without leading '_')."""
    tree = ast.parse(source_code)
    names: set[str] = set()
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and not node.name.startswith("_"):
            names.add(node.name)
        elif isinstance(node, ast.ClassDef):
            names.add(node.name)
            for sub in node.body:
                if isinstance(sub, ast.FunctionDef | ast.AsyncFunctionDef) and not sub.name.startswith("_"):
                    names.add(f"{node.name}.{sub.name}")
    return names


def api_preservation(original: str, refactored: str) -> dict[str, Any]:
    """Check that every public name in the original survives in the refactored code.

    Returns a dict with `preserved` (bool) plus the diff for diagnostics. A refactoring
    that drops or renames a public function/class/method without keeping a compatible
    entry point fails this check.
    """
    try:
        original_api = extract_public_api(original)
    except SyntaxError:
        original_api = set()
    try:
        refactored_api = extract_public_api(refactored)
    except SyntaxError:
        return {
            "preserved": False,
            "reason": "refactored code has a syntax error",
            "missing": sorted(original_api),
            "original_api": sorted(original_api),
            "refactored_api": [],
        }
    missing = sorted(original_api - refactored_api)
    return {
        "preserved": not missing,
        "missing": missing,
        "original_api": sorted(original_api),
        "refactored_api": sorted(refactored_api),
    }


def assess_refactoring(
    original: str,
    refactored: str,
    applied_pattern: DesignPatternType,
    expected_pattern: DesignPatternType,
) -> dict[str, Any]:
    """Aggregate the three objective checks into a single verdict.

    `is_correct` requires all three: correct pattern, valid syntax and preserved public API.
    """
    pattern_ok = pattern_matches(applied_pattern, expected_pattern)
    syntax = check_syntax(refactored)
    syntax_ok = bool(syntax.get("is_valid"))
    api = api_preservation(original, refactored)
    api_ok = bool(api.get("preserved"))
    return {
        "pattern_correct": pattern_ok,
        "syntax_valid": syntax_ok,
        "logic_preserved": api_ok,
        "is_correct": pattern_ok and syntax_ok and api_ok,
        "syntax_detail": syntax,
        "api_detail": api,
    }
