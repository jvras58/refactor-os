"""Tests for the heuristic smell matrix (deterministic, no LLM)."""
from __future__ import annotations

import pytest

from app.core.schemas import SmellType
from app.tools.heuristic_engine import score_all_smells


def test_all_smells_always_have_a_slot(clean_code):
    result = score_all_smells(clean_code)
    assert set(result.keys()) == set(SmellType)


def test_clean_code_triggers_no_signal(clean_code):
    result = score_all_smells(clean_code)
    assert all(signal is None for signal in result.values())


def test_long_parameter_list_triggers(long_params_code):
    signal = score_all_smells(long_params_code)[SmellType.LONG_PARAMETER]
    assert signal is not None
    assert signal.smell == SmellType.LONG_PARAMETER
    assert 0.0 < signal.score <= 1.0
    assert signal.line_start is not None


def test_god_class_triggers(god_class_code):
    signal = score_all_smells(god_class_code)[SmellType.GOD_CLASS]
    assert signal is not None
    assert signal.evidence


def test_complex_switch_triggers(high_complexity_code):
    signal = score_all_smells(high_complexity_code)[SmellType.COMPLEX_SWITCH]
    assert signal is not None


def test_duplicated_code_triggers():
    method = "\n".join(
        [
            "    def process(self):",
            "        a = 1",
            "        b = a + 1",
            "        return b",
        ]
    )
    code = f"class A:\n{method}\n\nclass B:\n{method}\n"
    signal = score_all_smells(code)[SmellType.DUPLICATED_CODE]
    assert signal is not None


def test_syntax_error_raises(broken_code):
    with pytest.raises(SyntaxError):
        score_all_smells(broken_code)
