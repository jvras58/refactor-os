"""Deterministic logic-preservation signals between original and refactored code.

This is the Critic's counterpart to the Detector's heuristic matrix
(``app/tools/heuristic_engine.py``): a pure, LLM-free analysis that compares the
**behavioural tokens** of the original code against the refactored one and
surfaces what *disappeared*. It is injected into the Critic prompt as evidence
for "Critério 2 — Lógica preservada"; the Critic still decides.

Why behavioural tokens (and not a textual diff): a legitimate refactor reshapes
structure (an ``if/elif`` chain becomes a dict of strategies, a god class is
split, etc.) but **keeps the same constants, raised exceptions and calls** —
just reorganised. So a value that vanishes entirely is a strong, low-noise
signal that a branch/rule was dropped (e.g. a missing ``18.0``/``"JP"`` means a
shipping rule was lost). Docstrings are ignored so comments/headers don't create
false differences.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass, field


@dataclass
class LogicReport:
    """What is present in the original but missing in the refactored code."""

    lost_literals: list[str] = field(default_factory=list)
    lost_raises: list[str] = field(default_factory=list)
    lost_calls: list[str] = field(default_factory=list)
    original_counts: dict[str, int] = field(default_factory=dict)
    refactored_counts: dict[str, int] = field(default_factory=dict)
    refactored_parse_error: str | None = None

    @property
    def has_strong_signal(self) -> bool:
        """A lost literal or lost raised exception strongly suggests altered logic."""
        return bool(self.lost_literals or self.lost_raises)


def _is_docstring(node: ast.AST, parent_body_first: ast.AST | None) -> bool:
    return node is parent_body_first and isinstance(node, ast.Expr) and isinstance(
        getattr(node, "value", None), ast.Constant
    ) and isinstance(node.value.value, str)


def _collect(tree: ast.AST) -> dict[str, object]:
    literals: set[str] = set()
    raises: set[str] = set()
    calls: set[str] = set()
    counts = {"if": 0, "for": 0, "while": 0, "try": 0, "return": 0, "raise": 0}

    # Identify docstring nodes (module/class/function first statement) to skip.
    docstrings: set[int] = set()
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if isinstance(body, list) and body and _is_docstring(body[0], body[0]):
            docstrings.add(id(body[0].value))

    for node in ast.walk(tree):
        if isinstance(node, ast.Constant):
            if id(node) in docstrings:
                continue
            if isinstance(node.value, bool) or node.value is None:
                continue
            if isinstance(node.value, (int, float, complex, str, bytes)):
                literals.add(repr(node.value))
        elif isinstance(node, ast.Raise) and node.exc is not None:
            exc = node.exc.func if isinstance(node.exc, ast.Call) else node.exc
            name = exc.id if isinstance(exc, ast.Name) else (
                exc.attr if isinstance(exc, ast.Attribute) else None
            )
            if name:
                raises.add(name)
        elif isinstance(node, ast.Call):
            func = node.func
            name = func.id if isinstance(func, ast.Name) else (
                func.attr if isinstance(func, ast.Attribute) else None
            )
            if name:
                calls.add(name)

        if isinstance(node, ast.If):
            counts["if"] += 1
        elif isinstance(node, (ast.For, ast.AsyncFor)):
            counts["for"] += 1
        elif isinstance(node, ast.While):
            counts["while"] += 1
        elif isinstance(node, ast.Try):
            counts["try"] += 1
        elif isinstance(node, ast.Return):
            counts["return"] += 1
        elif isinstance(node, ast.Raise):
            counts["raise"] += 1

    # Calls that merely construct a raised exception are already covered by `raises`.
    calls -= raises
    return {"literals": literals, "raises": raises, "calls": calls, "counts": counts}


def analyze_logic_preservation(original: str, refactored: str) -> LogicReport:
    """Compare behavioural tokens; report what the refactor dropped."""
    try:
        original_tree = ast.parse(original)
    except SyntaxError:
        return LogicReport()  # nothing to compare against
    try:
        refactored_tree = ast.parse(refactored)
    except SyntaxError as exc:
        return LogicReport(refactored_parse_error=f"{exc.msg} (linha {exc.lineno})")

    orig = _collect(original_tree)
    refac = _collect(refactored_tree)

    return LogicReport(
        lost_literals=sorted(orig["literals"] - refac["literals"]),  # type: ignore[operator]
        lost_raises=sorted(orig["raises"] - refac["raises"]),  # type: ignore[operator]
        lost_calls=sorted(orig["calls"] - refac["calls"]),  # type: ignore[operator]
        original_counts=orig["counts"],  # type: ignore[arg-type]
        refactored_counts=refac["counts"],  # type: ignore[arg-type]
    )


def format_logic_prior(report: LogicReport) -> str:
    """Render the report as a prompt block for the Critic."""
    if report.refactored_parse_error:
        return (
            "Prior de preservação de lógica: o código refatorado NÃO compila "
            f"({report.refactored_parse_error}) — Critério 1 (sintaxe) já falha."
        )

    lines: list[str] = []
    if report.lost_literals:
        lines.append(
            f"- Literais presentes no original e AUSENTES no refatorado: {', '.join(report.lost_literals)}. "
            "Forte indício de que uma regra/ramo/valor foi descartado — verifique."
        )
    if report.lost_raises:
        lines.append(
            f"- Exceções levantadas no original e ausentes no refatorado: {', '.join(report.lost_raises)}. "
            "Possível perda de tratamento de erro."
        )
    if report.lost_calls:
        lines.append(
            f"- Chamadas presentes no original e ausentes no refatorado: {', '.join(report.lost_calls)} (sinal fraco — pode ser legítimo)."
        )

    if not lines:
        return (
            "Prior de preservação de lógica: nenhuma divergência estrutural detectada "
            "(literais, exceções e chamadas do original preservados no refatorado). "
            "Confirme a equivalência funcional via diff."
        )

    deltas = (
        f"Contagens original→refatorado: ramos if {report.original_counts.get('if')}→"
        f"{report.refactored_counts.get('if')}, returns {report.original_counts.get('return')}→"
        f"{report.refactored_counts.get('return')}, raises {report.original_counts.get('raise')}→"
        f"{report.refactored_counts.get('raise')}."
    )
    return (
        "Prior de preservação de lógica (análise estática determinística):\n"
        + "\n".join(lines)
        + f"\n{deltas}\n"
        "Use como evidência no Critério 2; o prior NÃO decide — você pode justificar "
        "uma divergência se houver equivalente funcional no código."
    )
