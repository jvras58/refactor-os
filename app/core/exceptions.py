"""Domain exceptions raised by the refactoring pipeline."""
from __future__ import annotations


class InvalidPythonCodeError(Exception):
    """Raised in phase 1 of the detector when the input does not compile as Python source."""

    def __init__(self, message: str, line: int | None = None) -> None:
        self.line = line
        super().__init__(message)
