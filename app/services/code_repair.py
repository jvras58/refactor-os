"""Deterministic sanitisation of LLM-generated refactored code.

Small local models, when emitting a multi-line code block as a JSON string,
occasionally drop the indentation of the line *after a decorator* — e.g.:

    class Strategy(ABC):
        @abstractmethod
    def run(self):          # <- emitted at column 0, breaks the file
            ...

The rest of the file is fine, so this single artifact would otherwise flip
``syntax_valid`` to false. ``repair_refactored_code`` re-indents a ``def``/
``class`` line that follows a decorator to match the decorator's indent. It is
purely structural (never changes tokens/logic) and is a no-op on well-formed
code, so it is safe to run on every proposal regardless of the model.
"""
from __future__ import annotations

_BLOCK_STARTS = ("def ", "async def ", "class ")


def _indent_of(line: str) -> int:
    return len(line) - len(line.lstrip())


def repair_refactored_code(code: str) -> str:
    """Re-indent a def/class that follows a decorator but lost its indentation."""
    if "@" not in code:
        return code

    lines = code.splitlines()
    out = list(lines)
    for i, line in enumerate(lines):
        if not line.strip().startswith("@"):
            continue
        decorator_indent = _indent_of(line)

        nxt = i + 1
        while nxt < len(lines) and not lines[nxt].strip():
            nxt += 1
        if nxt >= len(lines):
            continue

        following = lines[nxt]
        stripped = following.strip()
        if _indent_of(following) < decorator_indent and stripped.startswith(_BLOCK_STARTS):
            out[nxt] = " " * decorator_indent + stripped

    repaired = "\n".join(out)
    if code.endswith("\n") and not repaired.endswith("\n"):
        repaired += "\n"
    return repaired
