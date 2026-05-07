"""Unit tests for the AST analyzer tool (deterministic, no LLM)."""
from __future__ import annotations

from app.tools.ast_tools import analyze_ast


def test_analyze_ast_handles_syntax_error():
    result = analyze_ast("def broken(:")
    assert "error" in result


def test_analyze_ast_detects_long_parameter_list():
    code = "def f(a, b, c, d, e):\n    return a+b+c+d+e\n"
    out = analyze_ast(code)
    long_params = out["long_parameter_functions"]
    assert any(item["name"] == "f" and item["params"] == 5 for item in long_params)


def test_analyze_ast_detects_god_class():
    body = "\n".join(f"    def m{i}(self): return {i}" for i in range(25))
    code = f"class Big:\n{body}\n"
    out = analyze_ast(code)
    god = out["god_classes"]
    assert any(item["name"] == "Big" and item["members"] >= 21 for item in god)


def test_analyze_ast_flags_high_complexity():
    branches = "\n".join(
        f"    elif x == {i}: return {i}" for i in range(1, 15)
    )
    code = f"def big(x):\n    if x == 0: return 0\n{branches}\n    else: return -1\n"
    out = analyze_ast(code)
    assert any(b["complexity"] > 10 for b in out["high_complexity_blocks"])


def test_analyze_ast_clean_code_returns_no_issues():
    code = "def add(a, b):\n    return a + b\n"
    out = analyze_ast(code)
    assert out["god_classes"] == []
    assert out["long_parameter_functions"] == []
    assert out["high_complexity_blocks"] == []
