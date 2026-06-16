"""Behaviour-preservation axis of assess_refactoring (no LLM).

Regression: a Strategy refactoring that keeps the public function as a thin
wrapper but drops the ``else: raise ValueError(...)`` branch must NOT count as
correct — the public API is preserved, but the behaviour is not.
"""
from __future__ import annotations

from app.core.schemas import DesignPatternType
from app.services.quality_checks import assess_refactoring

_ORIGINAL = (
    "def calculate_shipping(country, weight_kg):\n"
    "    if country == 'BR':\n"
    "        return 15.0\n"
    "    elif country == 'JP':\n"
    "        return 18.0 + weight_kg * 4.5\n"
    "    else:\n"
    "        raise ValueError(f'unsupported country: {country}')\n"
)

_DROPS_EXCEPTION = (
    "class S:\n"
    "    def calculate(self, weight_kg): raise NotImplementedError()\n"
    "class BR(S):\n"
    "    def calculate(self, weight_kg): return 15.0\n"
    "class JP(S):\n"
    "    def calculate(self, weight_kg): return 18.0 + weight_kg * 4.5\n"
    "def get_strategy(country):\n"
    "    return {'BR': BR, 'JP': JP}[country]()\n"
    "def calculate_shipping(country, weight_kg):\n"
    "    return get_strategy(country).calculate(weight_kg)\n"
)

_FAITHFUL = (
    "class S:\n"
    "    def calculate(self, weight_kg): raise NotImplementedError()\n"
    "class BR(S):\n"
    "    def calculate(self, weight_kg): return 15.0\n"
    "class JP(S):\n"
    "    def calculate(self, weight_kg): return 18.0 + weight_kg * 4.5\n"
    "def get_strategy(country):\n"
    "    s = {'BR': BR, 'JP': JP}.get(country)\n"
    "    if s is None:\n"
    "        raise ValueError(f'unsupported country: {country}')\n"
    "    return s()\n"
    "def calculate_shipping(country, weight_kg):\n"
    "    return get_strategy(country).calculate(weight_kg)\n"
)


def test_dropping_exception_is_not_correct():
    a = assess_refactoring(_ORIGINAL, _DROPS_EXCEPTION, DesignPatternType.STRATEGY, DesignPatternType.STRATEGY)
    assert a["api_preserved"] is True          # wrapper keeps calculate_shipping
    assert a["behavior_preserved"] is False    # but ValueError + literals were dropped
    assert a["is_correct"] is False
    assert "ValueError" in a["behavior_detail"]["lost_raises"]


def test_faithful_refactor_is_correct():
    a = assess_refactoring(_ORIGINAL, _FAITHFUL, DesignPatternType.STRATEGY, DesignPatternType.STRATEGY)
    assert a["behavior_preserved"] is True
    assert a["is_correct"] is True
