"""Unit tests for the AST analyzer tool (deterministic, no LLM)."""
from __future__ import annotations

from app.tools.ast_tools import analyze_ast


def test_analyze_ast_handles_syntax_error(broken_code):
    result = analyze_ast(broken_code)
    assert "error" in result


def test_analyze_ast_detects_long_parameter_list(long_params_code):
    out = analyze_ast(long_params_code)
    long_params = out["long_parameter_functions"]
    assert any(item["name"] == "f" and item["params"] == 5 for item in long_params)


def test_analyze_ast_detects_god_class(god_class_code):
    out = analyze_ast(god_class_code)
    god = out["god_classes"]
    assert any(item["name"] == "Big" and item["members"] >= 21 for item in god)


def test_analyze_ast_flags_high_complexity(high_complexity_code):
    out = analyze_ast(high_complexity_code)
    assert any(b["complexity"] > 10 for b in out["high_complexity_blocks"])


def test_analyze_ast_clean_code_returns_no_issues(clean_code):
    out = analyze_ast(clean_code)
    assert out["god_classes"] == []
    assert out["long_parameter_functions"] == []
    assert out["high_complexity_blocks"] == []
