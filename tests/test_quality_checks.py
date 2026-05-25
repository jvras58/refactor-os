"""Deterministic tests for the offline refactoring-quality heuristics."""
from __future__ import annotations

from app.core.schemas import DesignPatternType
from app.services.quality_checks import (
    api_preservation,
    assess_refactoring,
    extract_public_api,
    pattern_matches,
)


def test_extract_public_api_ignores_private_members(original_code):
    api = extract_public_api(original_code)
    assert api == {"calculate", "Service", "Service.run"}


def test_api_preservation_detects_dropped_public_name(original_code, refactored_without_service):
    result = api_preservation(original_code, refactored_without_service)
    assert result["preserved"] is False
    assert "Service" in result["missing"]


def test_api_preservation_passes_when_names_kept(original_code):
    result = api_preservation(original_code, original_code)
    assert result["preserved"] is True
    assert result["missing"] == []


def test_api_preservation_fails_on_syntax_error(original_code, refactored_with_syntax_error):
    result = api_preservation(original_code, refactored_with_syntax_error)
    assert result["preserved"] is False


def test_pattern_matches():
    assert pattern_matches(DesignPatternType.STRATEGY, DesignPatternType.STRATEGY)
    assert not pattern_matches(DesignPatternType.STRATEGY, DesignPatternType.BUILDER)


def test_assess_refactoring_all_axes(original_code):
    good = assess_refactoring(
        original_code,
        original_code,
        DesignPatternType.STRATEGY,
        DesignPatternType.STRATEGY,
    )
    assert good["is_correct"] is True

    wrong_pattern = assess_refactoring(
        original_code,
        original_code,
        DesignPatternType.BUILDER,
        DesignPatternType.STRATEGY,
    )
    assert wrong_pattern["pattern_correct"] is False
    assert wrong_pattern["is_correct"] is False
