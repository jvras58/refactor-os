from app.tools.diff_tools import generate_diff


def test_generate_diff_marks_changes():
    original = "def f(): return 1\n"
    refactored = "def f(): return 2\n"
    diff = generate_diff(original, refactored)
    assert "-def f(): return 1" in diff
    assert "+def f(): return 2" in diff


def test_generate_diff_handles_identical_inputs():
    code = "x = 1\n"
    assert generate_diff(code, code) == "<no differences>"
