from app.tools.diff_tools import generate_diff


def test_generate_diff_marks_changes(diff_pair):
    diff = generate_diff(diff_pair["original"], diff_pair["refactored"])
    assert "-def f(): return 1" in diff
    assert "+def f(): return 2" in diff


def test_generate_diff_handles_identical_inputs(identical_code):
    assert generate_diff(identical_code, identical_code) == "<no differences>"
