from app.tools.syntax_tools import check_syntax


def test_check_syntax_valid_code(valid_code):
    out = check_syntax(valid_code)
    assert out["is_valid"] is True


def test_check_syntax_invalid_code_reports_error(invalid_code):
    out = check_syntax(invalid_code)
    assert out["is_valid"] is False
    assert "error" in out
    assert out["line"] is not None
