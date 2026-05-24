"""Deterministic tests for the offline refactoring-quality heuristics."""
from __future__ import annotations

from app.core.schemas import DesignPatternType
from app.services.quality_checks import (
    api_preservation,
    assess_refactoring,
    extract_public_api,
    pattern_matches,
)

ORIGINAL = """\
def calculate(x):
    return x


class Service:
    def run(self):
        return 1

    def _private(self):
        return 2
"""


def test_extract_public_api_ignores_private_members():
    api = extract_public_api(ORIGINAL)
    assert api == {"calculate", "Service", "Service.run"}


def test_api_preservation_detects_dropped_public_name():
    refactored = "def calculate(x):\n    return x\n"  # Service removida
    result = api_preservation(ORIGINAL, refactored)
    assert result["preserved"] is False
    assert "Service" in result["missing"]


def test_api_preservation_passes_when_names_kept():
    result = api_preservation(ORIGINAL, ORIGINAL)
    assert result["preserved"] is True
    assert result["missing"] == []


def test_api_preservation_fails_on_syntax_error():
    result = api_preservation(ORIGINAL, "def calculate(x)\n    return x\n")
    assert result["preserved"] is False


def test_pattern_matches():
    assert pattern_matches(DesignPatternType.STRATEGY, DesignPatternType.STRATEGY)
    assert not pattern_matches(DesignPatternType.STRATEGY, DesignPatternType.BUILDER)


def test_assess_refactoring_all_axes():
    good = assess_refactoring(ORIGINAL, ORIGINAL, DesignPatternType.STRATEGY, DesignPatternType.STRATEGY)
    assert good["is_correct"] is True

    wrong_pattern = assess_refactoring(ORIGINAL, ORIGINAL, DesignPatternType.BUILDER, DesignPatternType.STRATEGY)
    assert wrong_pattern["pattern_correct"] is False
    assert wrong_pattern["is_correct"] is False
