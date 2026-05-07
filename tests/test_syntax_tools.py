from app.tools.syntax_tools import check_syntax


def test_check_syntax_valid_code():
    out = check_syntax("def f(): return 42\n")
    assert out["is_valid"] is True


def test_check_syntax_invalid_code_reports_error():
    out = check_syntax("def f(:\n")
    assert out["is_valid"] is False
    assert "error" in out
    assert out["line"] is not None
