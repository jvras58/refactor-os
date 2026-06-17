"""Tests for the logic-preservation analyzer used as the Critic's prior."""
from __future__ import annotations

from app.tools.logic_signals import analyze_logic_preservation, format_logic_prior

_ORIGINAL = """\
def shipping(country, weight):
    if country == 'BR':
        return weight * 1.5
    if country == 'US':
        return weight * 2.0
    raise ValueError('unsupported country')
"""

# Strategy via lookup preservando literais, ramos e o raise do caso default.
_FAITHFUL = """\
_RATES = {'BR': 1.5, 'US': 2.0}


def shipping(country, weight):
    rate = _RATES.get(country)
    if rate is None:
        raise ValueError('unsupported country')
    return weight * rate
"""

# Perde o ramo default (raise ValueError) — defeito de lógica clássico.
_DROPS_BRANCH = """\
_RATES = {'BR': 1.5, 'US': 2.0}


def shipping(country, weight):
    return weight * _RATES[country]
"""


def test_correct_solution_has_no_strong_signal():
    """A logic-preserving refactor must not raise a false 'logic changed' flag."""
    report = analyze_logic_preservation(_ORIGINAL, _FAITHFUL)
    assert not report.has_strong_signal, (report.lost_literals, report.lost_raises)


def test_logic_defect_is_flagged():
    """A refactor that silently drops the default raise must trigger a strong signal."""
    report = analyze_logic_preservation(_ORIGINAL, _DROPS_BRANCH)
    assert report.has_strong_signal
    assert "ValueError" in report.lost_raises


def test_dropped_raise_is_reported():
    original = "def f(x):\n    if x < 0:\n        raise ValueError('neg')\n    return x\n"
    refactored = "def f(x):\n    return x\n"
    report = analyze_logic_preservation(original, refactored)
    assert "ValueError" in report.lost_raises
    assert "'neg'" in report.lost_literals
    assert report.has_strong_signal


def test_identical_code_is_clean():
    code = "def f(x):\n    return x + 1\n"
    report = analyze_logic_preservation(code, code)
    assert not report.has_strong_signal
    assert "nenhuma divergência" in format_logic_prior(report).lower()


def test_refactored_syntax_error_is_surfaced():
    report = analyze_logic_preservation("x = 1\n", "def broken(:\n")
    assert report.refactored_parse_error is not None
    assert "não compila" in format_logic_prior(report).lower()


def test_docstring_change_is_ignored():
    original = '"""Old header."""\ndef f():\n    return 42\n'
    refactored = '"""Totally different header text."""\ndef f():\n    return 42\n'
    report = analyze_logic_preservation(original, refactored)
    assert not report.has_strong_signal
