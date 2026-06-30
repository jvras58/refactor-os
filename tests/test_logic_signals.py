"""Tests for the logic-preservation analyzer used as the Critic's prior."""
from __future__ import annotations

import json

from app.tools.logic_signals import analyze_logic_preservation, format_logic_prior


def _pairs(dataset_root):
    truth = json.loads((dataset_root / "critic_truth.json").read_text(encoding="utf-8"))
    for entry in truth:
        original = (dataset_root / entry["problem_file"]).read_text(encoding="utf-8")
        refactored = (dataset_root / entry["solution_file"]).read_text(encoding="utf-8")
        yield entry, original, refactored


def test_correct_solutions_have_no_strong_signal(dataset_root):
    """A logic-preserving refactor must not raise a false 'logic changed' flag."""
    false_positives = []
    for entry, original, refactored in _pairs(dataset_root):
        if not entry["expected_approved"]:
            continue
        report = analyze_logic_preservation(original, refactored)
        if report.has_strong_signal:
            false_positives.append((entry["solution_file"], report.lost_literals, report.lost_raises))
    assert not false_positives, f"false logic-change signals on correct solutions: {false_positives}"


def test_logic_defects_are_flagged(dataset_root):
    """Every solution labeled with a 'logic' defect must trigger a strong signal."""
    misses = []
    for entry, original, refactored in _pairs(dataset_root):
        if entry.get("defect_kind") != "logic":
            continue
        report = analyze_logic_preservation(original, refactored)
        if not report.has_strong_signal:
            misses.append(entry["solution_file"])
    assert not misses, f"logic defects not detected: {misses}"


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
