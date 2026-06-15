"""Logic-preservation signals between original and refactored code.

The Critic's deterministic prior (counterpart to the Detector's heuristic
matrix): it reports the literals, raised exceptions and calls that existed in
the original but vanished after the refactor — strong evidence that a rule or
branch was dropped. Structural refactors keep these tokens (an if/elif chain
becomes a dict of strategies, a god class is split), so the signal is low-noise.
Docstrings are ignored so headers/comments don't count as differences.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass, field

_COUNTED: dict[type[ast.AST], str] = {
    ast.If: "if",
    ast.For: "for",
    ast.AsyncFor: "for",
    ast.While: "while",
    ast.Try: "try",
    ast.Return: "return",
    ast.Raise: "raise",
}


@dataclass(frozen=True)
class _Tokens:
    literals: set[str]
    raises: set[str]
    calls: set[str]
    counts: dict[str, int]


@dataclass
class LogicReport:
    """What the original code had that the refactored code no longer has."""

    lost_literals: list[str] = field(default_factory=list)
    lost_raises: list[str] = field(default_factory=list)
    lost_calls: list[str] = field(default_factory=list)
    original_counts: dict[str, int] = field(default_factory=dict)
    refactored_counts: dict[str, int] = field(default_factory=dict)
    refactored_parse_error: str | None = None

    @property
    def has_strong_signal(self) -> bool:
        """A lost literal or raised exception strongly suggests altered logic."""
        return bool(self.lost_literals or self.lost_raises)


def _docstring_ids(tree: ast.AST) -> set[int]:
    """Object ids of Constant nodes that are module/class/function docstrings."""
    ids: set[int] = set()
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if isinstance(body, list) and body:
            first = body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) \
                    and isinstance(first.value.value, str):
                ids.add(id(first.value))
    return ids


def _name_of(node: ast.expr | None) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _collect(tree: ast.AST) -> _Tokens:
    docstrings = _docstring_ids(tree)
    literals: set[str] = set()
    raises: set[str] = set()
    calls: set[str] = set()
    counts = dict.fromkeys(("if", "for", "while", "try", "return", "raise"), 0)

    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and id(node) not in docstrings:
            if isinstance(node.value, (int, float, complex, str, bytes)) and not isinstance(node.value, bool):
                literals.add(repr(node.value))
        elif isinstance(node, ast.Raise) and node.exc is not None:
            exc = node.exc.func if isinstance(node.exc, ast.Call) else node.exc
            if name := _name_of(exc):
                raises.add(name)
        elif isinstance(node, ast.Call):
            if name := _name_of(node.func):
                calls.add(name)

        if key := _COUNTED.get(type(node)):
            counts[key] += 1

    return _Tokens(literals, raises, calls - raises, counts)


def analyze_logic_preservation(original: str, refactored: str) -> LogicReport:
    """Compare behavioural tokens and report what the refactor dropped."""
    try:
        before = _collect(ast.parse(original))
    except SyntaxError:
        return LogicReport()
    try:
        after = _collect(ast.parse(refactored))
    except SyntaxError as exc:
        return LogicReport(refactored_parse_error=f"{exc.msg} (linha {exc.lineno})")

    return LogicReport(
        lost_literals=sorted(before.literals - after.literals),
        lost_raises=sorted(before.raises - after.raises),
        lost_calls=sorted(before.calls - after.calls),
        original_counts=before.counts,
        refactored_counts=after.counts,
    )


def format_logic_prior(report: LogicReport) -> str:
    """Render the report as a prompt block for the Critic (Critério 2)."""
    if report.refactored_parse_error:
        return (
            f"Prior de preservação de lógica: o código refatorado não compila "
            f"({report.refactored_parse_error}); o Critério 1 já falha."
        )

    items: list[str] = []
    if report.lost_literals:
        items.append(
            f"Literais que sumiram do refatorado: {', '.join(report.lost_literals)} "
            "— forte indício de regra/ramo descartado."
        )
    if report.lost_raises:
        items.append(f"Exceções que deixaram de ser levantadas: {', '.join(report.lost_raises)}.")
    if report.lost_calls:
        items.append(f"Chamadas ausentes no refatorado: {', '.join(report.lost_calls)} (sinal fraco).")

    if not items:
        return (
            "Prior de preservação de lógica: nenhuma divergência detectada — literais, "
            "exceções e chamadas do original seguem presentes. Confirme a equivalência via diff."
        )
    return (
        "Prior de preservação de lógica (use como evidência no Critério 2; "
        "só aceite divergência com equivalente funcional explícito):\n- " + "\n- ".join(items)
    )
