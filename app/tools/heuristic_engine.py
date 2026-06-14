"""Heuristic matrix that ranks the 5 in-scope bad smells from AST signals.

The deterministic *prior* of the Detector: ``score_smells`` scores each smell
from explicit structural signals and the Detector LLM confirms/overrides it (see
``RefactorService.detect``). Scores in [0, 1] only rank candidates — they are not
calibrated probabilities.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass, field

from app.core.schemas import BadSmellType

# Thresholds shared with app/tools/ast_tools.py — kept in sync intentionally.
GOD_CLASS_MEMBER_THRESHOLD = 20
LONG_PARAMETER_THRESHOLD = 5
HIGH_COMPLEXITY_THRESHOLD = 10
SWITCH_BRANCH_THRESHOLD = 3
DUPLICATE_MIN_STATEMENTS = 3


@dataclass
class SmellSignal:
    """A single ranked smell candidate produced by the heuristic matrix."""

    smell: BadSmellType
    score: float
    evidence: list[str] = field(default_factory=list)
    line_start: int | None = None
    line_end: int | None = None

    def as_dict(self) -> dict:
        return {
            "smell_type": self.smell.value,
            "score": round(self.score, 3),
            "evidence": self.evidence,
            "line_start": self.line_start,
            "line_end": self.line_end,
        }


def _branch_count(node: ast.AST) -> int:
    """Count elif arms in an if-chain or case arms in a match statement."""
    if isinstance(node, ast.Match):
        return len(node.cases)
    count = 0
    current = node
    while isinstance(current, ast.If):
        count += 1
        # ``elif`` is encoded as a nested If inside orelse.
        if len(current.orelse) == 1 and isinstance(current.orelse[0], ast.If):
            current = current.orelse[0]
        else:
            if current.orelse:
                count += 1  # trailing else
            break
    return count


def _score_complex_switch(tree: ast.AST) -> SmellSignal | None:
    best: tuple[int, ast.AST] | None = None
    for node in ast.walk(tree):
        if isinstance(node, (ast.If, ast.Match)):
            # Skip If nodes that are merely the elif of an outer chain.
            branches = _branch_count(node)
            if branches >= SWITCH_BRANCH_THRESHOLD and (best is None or branches > best[0]):
                best = (branches, node)
    if best is None:
        return None
    branches, node = best
    score = min(1.0, 0.4 + 0.1 * branches)
    kind = "match/case" if isinstance(node, ast.Match) else "if/elif"
    return SmellSignal(
        smell=BadSmellType.COMPLEX_SWITCH,
        score=score,
        evidence=[f"Cadeia {kind} com {branches} ramos (limite {SWITCH_BRANCH_THRESHOLD})."],
        line_start=getattr(node, "lineno", None),
        line_end=getattr(node, "end_lineno", None),
    )


def _score_long_parameter(tree: ast.AST) -> SmellSignal | None:
    worst: tuple[int, ast.AST] | None = None
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            params = len(node.args.args) + len(node.args.kwonlyargs)
            if params >= LONG_PARAMETER_THRESHOLD and (worst is None or params > worst[0]):
                worst = (params, node)
    if worst is None:
        return None
    params, node = worst
    score = min(1.0, 0.4 + 0.1 * (params - LONG_PARAMETER_THRESHOLD + 1))
    return SmellSignal(
        smell=BadSmellType.LONG_PARAMETER,
        score=score,
        evidence=[f"Função `{node.name}` com {params} parâmetros (limite {LONG_PARAMETER_THRESHOLD})."],
        line_start=node.lineno,
        line_end=getattr(node, "end_lineno", None),
    )


def _class_member_count(cls: ast.ClassDef) -> int:
    """Methods plus distinct ``self.x`` attributes — a responsibilities proxy."""
    methods = sum(
        1 for n in cls.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    )
    attributes: set[str] = set()
    for node in ast.walk(cls):
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            if node.value.id == "self" and isinstance(node.ctx, ast.Store):
                attributes.add(node.attr)
    return methods + len(attributes)


def _score_god_class(tree: ast.AST) -> SmellSignal | None:
    worst: tuple[int, ast.ClassDef] | None = None
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            members = _class_member_count(node)
            if members > GOD_CLASS_MEMBER_THRESHOLD and (worst is None or members > worst[0]):
                worst = (members, node)
    if worst is None:
        return None
    members, node = worst
    score = min(1.0, 0.5 + 0.05 * (members - GOD_CLASS_MEMBER_THRESHOLD))
    return SmellSignal(
        smell=BadSmellType.GOD_CLASS,
        score=score,
        evidence=[f"Classe `{node.name}` com {members} membros (métodos + atributos; limite {GOD_CLASS_MEMBER_THRESHOLD})."],
        line_start=node.lineno,
        line_end=getattr(node, "end_lineno", None),
    )


def _hardcoded_dep_name(func: ast.expr) -> str | None:
    """Name of a hardcoded collaborator: a class ``Foo(...)`` or a qualified
    factory ``mod.connect(...)``. Bare builtin calls (``list()``) return None."""
    if isinstance(func, ast.Name):
        return func.id if func.id[:1].isupper() else None
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _assigns_to_self(targets: list[ast.expr]) -> bool:
    return any(
        isinstance(t, ast.Attribute)
        and isinstance(t.value, ast.Name)
        and t.value.id == "self"
        for t in targets
    )


def _score_tight_coupling(tree: ast.AST) -> SmellSignal | None:
    """Concrete collaborators instantiated inside a class (no injection point)."""
    hits: list[tuple[str, int]] = []
    for cls in ast.walk(tree):
        if not isinstance(cls, ast.ClassDef):
            continue
        for node in ast.walk(cls):
            # self.x = SomeClass(...) / sqlite3.connect(...) — built, not injected.
            if (
                isinstance(node, ast.Assign)
                and isinstance(node.value, ast.Call)
                and _assigns_to_self(node.targets)
            ):
                name = _hardcoded_dep_name(node.value.func)
                if name is not None:
                    hits.append((name, node.lineno))
    if not hits:
        return None
    names = ", ".join(sorted({n for n, _ in hits}))
    score = min(1.0, 0.4 + 0.15 * len(hits))
    return SmellSignal(
        smell=BadSmellType.TIGHT_COUPLING,
        score=score,
        evidence=[f"{len(hits)} instanciações concretas dentro de classe (sem injeção): {names}."],
        line_start=min(line for _, line in hits),
        line_end=max(line for _, line in hits),
    )


def _score_duplicated_code(tree: ast.AST) -> SmellSignal | None:
    """Same-named, substantial methods spread across >=2 classes.

    This is the Template Method signal: sibling classes re-implementing the same
    operation with a shared skeleton. Tiny overrides (e.g. abstract ``...`` stubs)
    are excluded so already-refactored code does not trigger a false positive.
    """
    by_name: dict[str, list[tuple[str, ast.AST]]] = {}
    for cls in ast.walk(tree):
        if not isinstance(cls, ast.ClassDef):
            continue
        for node in cls.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if len(node.body) >= DUPLICATE_MIN_STATEMENTS:
                    by_name.setdefault(node.name, []).append((cls.name, node))

    for method, occurrences in by_name.items():
        classes = {cls_name for cls_name, _ in occurrences}
        if len(classes) >= 2:
            nodes = [node for _, node in occurrences]
            owners = ", ".join(sorted(classes))
            return SmellSignal(
                smell=BadSmellType.DUPLICATED_CODE,
                score=min(1.0, 0.4 + 0.15 * len(classes)),
                evidence=[f"Método `{method}` reimplementado em {len(classes)} classes: {owners}."],
                line_start=nodes[0].lineno,
                line_end=getattr(nodes[-1], "end_lineno", None),
            )
    return None


_DETECTORS = (
    _score_complex_switch,
    _score_long_parameter,
    _score_god_class,
    _score_tight_coupling,
    _score_duplicated_code,
)


def score_smells(source_code: str) -> list[SmellSignal]:
    """Return probable smells ranked by descending heuristic score.

    Empty list means no in-scope smell triggered any heuristic — a strong prior
    for ``NO_SMELL`` that the Detector should only override with clear evidence.
    """
    try:
        tree = ast.parse(source_code)
    except SyntaxError:
        return []

    signals = [signal for detector in _DETECTORS if (signal := detector(tree)) is not None]
    signals.sort(key=lambda s: s.score, reverse=True)
    return signals


def format_prior(signals: list[SmellSignal]) -> str:
    """Render the ranked signals as a prompt block for the Detector."""
    if not signals:
        return (
            "Nenhum smell do escopo disparou a matriz heurística. "
            "Prior forte para `No Smell Detected` — só contrarie com evidência clara no código."
        )
    lines = ["Smells prováveis segundo a matriz heurística (ordenados por score):"]
    for rank, sig in enumerate(signals, start=1):
        evidence = " ".join(sig.evidence)
        location = f"linhas {sig.line_start}-{sig.line_end}" if sig.line_start else "linha n/d"
        lines.append(f"{rank}. {sig.smell.value} (score {sig.score:.2f}, {location}) — {evidence}")
    lines.append(
        "Confirme ou refute o candidato de maior score com base no código. "
        "A decisão final é sua, mas justifique divergências do prior."
    )
    return "\n".join(lines)
