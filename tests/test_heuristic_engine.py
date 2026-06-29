"""Tests for the heuristic smell matrix (deterministic, no LLM).

Locks in the prior's behaviour over the labeled dataset: it must rank the
correct smell first on every smelly example and stay silent on clean code.
"""
from __future__ import annotations

import json

import pytest

from app.tools.heuristic_engine import format_prior, score_smells


def _ground_truth(dataset_root):
    raw = json.loads((dataset_root / "ground_truth.json").read_text(encoding="utf-8"))
    return {entry["file"].split("/")[-1]: entry["smell_type"] for entry in raw}


def test_top_signal_matches_ground_truth(dataset_root):
    gt = _ground_truth(dataset_root)
    misses = []
    for path in sorted((dataset_root / "examples").glob("*.py")):
        signals = score_smells(path.read_text(encoding="utf-8"))
        top = signals[0].smell.value if signals else "No Smell Detected"
        expected = gt.get(path.name)
        if expected and top != expected:
            misses.append((path.name, top, expected))
    assert not misses, f"heuristic mis-ranked: {misses}"


def test_clean_code_triggers_no_signal(dataset_root):
    false_positives = []
    for path in sorted((dataset_root / "clean").glob("*.py")):
        if score_smells(path.read_text(encoding="utf-8")):
            false_positives.append(path.name)
    assert not false_positives, f"false positives on clean code: {false_positives}"


def test_syntax_error_yields_empty_prior():
    assert score_smells("def broken(:") == []


def test_format_prior_empty_signals_states_no_smell():
    assert "No Smell Detected" in format_prior([])


def test_format_prior_lists_ranked_candidates():
    signals = score_smells("def f(a, b, c, d, e):\n    return a + b + c + d + e\n")
    prior = format_prior(signals)
    assert "Long Parameter List" in prior
    assert "score" in prior


@pytest.mark.parametrize(
    "code, expected",
    [
        ("def f(a, b, c, d, e):\n    return 1\n", "Long Parameter List"),
    ],
)
def test_known_snippet(code, expected):
    signals = score_smells(code)
    assert signals and signals[0].smell.value == expected
