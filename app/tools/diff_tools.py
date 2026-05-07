"""Diff generation tool for the Critic agent."""
from __future__ import annotations

import difflib

from agno.tools import tool


def generate_diff(original: str, refactored: str) -> str:
    diff = difflib.unified_diff(
        original.splitlines(keepends=True),
        refactored.splitlines(keepends=True),
        fromfile="original.py",
        tofile="refactored.py",
        n=3,
    )
    return "".join(diff) or "<no differences>"


@tool(
    name="diff_generator_tool",
    description="Gera diff unificado entre código original e refatorado.",
)
def diff_generator_tool(original: str, refactored: str) -> str:
    return generate_diff(original, refactored)
