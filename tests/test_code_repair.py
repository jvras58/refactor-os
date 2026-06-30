"""Tests for the deterministic refactored-code sanitiser."""
from __future__ import annotations

import ast

from app.services.code_repair import repair_refactored_code


def test_reindents_def_after_decorator():
    broken = (
        "class S(ABC):\n"
        "    @abstractmethod\n"
        "def run(self):\n"
        "        return 1\n"
    )
    fixed = repair_refactored_code(broken)
    ast.parse(fixed)  # would raise SyntaxError before the repair
    assert "    def run(self):" in fixed


def test_handles_async_and_class_after_decorator():
    broken = "class C:\n    @deco\nasync def go(self):\n        return 1\n"
    fixed = repair_refactored_code(broken)
    ast.parse(fixed)
    assert "    async def go(self):" in fixed


def test_noop_on_wellformed_code():
    good = (
        "class S(ABC):\n"
        "    @abstractmethod\n"
        "    def run(self):\n"
        "        return 1\n"
    )
    assert repair_refactored_code(good) == good


def test_noop_without_decorators():
    code = "def add(a, b):\n    return a + b\n"
    assert repair_refactored_code(code) == code
