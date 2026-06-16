"""Exceptions raised by the multi-smell/multi-pattern detector pipeline."""
from __future__ import annotations


class InvalidPythonCodeError(Exception):
    """Raised in phase 1 when the input does not compile as Python source."""

    def __init__(self, message: str, line: int | None = None) -> None:
        self.line = line
        super().__init__(message)
