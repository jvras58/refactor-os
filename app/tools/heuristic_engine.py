"""Heuristic matrix that scores the 4 in-scope bad smells from AST signals.

The deterministic *prior* of the Detector: ``score_all_smells`` scores each smell
from explicit structural signals and the multi-detector's phase-3 LLM calls
confirm/override it (see ``MultiDetectorService``). Scores in [0, 1] only rank
candidates — they are not calibrated probabilities.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass, field

from app.core.schemas import SmellType

GOD_CLASS_MEMBER_THRESHOLD = 20
LONG_PARAMETER_THRESHOLD = 5
HIGH_COMPLEXITY_THRESHOLD = 10
SWITCH_BRANCH_THRESHOLD = 3
DUPLICATE_MIN_STATEMENTS = 3


@dataclass
class SmellSignal:
    """A single ranked smell candidate produced by the heuristic matrix."""

    smell: SmellType
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
        smell=SmellType.COMPLEX_SWITCH,
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
        smell=SmellType.LONG_PARAMETER,
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
        smell=SmellType.GOD_CLASS,
        score=score,
        evidence=[f"Classe `{node.name}` com {members} membros (métodos + atributos; limite {GOD_CLASS_MEMBER_THRESHOLD})."],
        line_start=node.lineno,
        line_end=getattr(node, "end_lineno", None),
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
                smell=SmellType.DUPLICATED_CODE,
                score=min(1.0, 0.4 + 0.15 * len(classes)),
                evidence=[f"Método `{method}` reimplementado em {len(classes)} classes: {owners}."],
                line_start=nodes[0].lineno,
                line_end=getattr(nodes[-1], "end_lineno", None),
            )
    return None


_SCORERS_BY_SMELL = {
    SmellType.COMPLEX_SWITCH: _score_complex_switch,
    SmellType.LONG_PARAMETER: _score_long_parameter,
    SmellType.GOD_CLASS: _score_god_class,
    SmellType.DUPLICATED_CODE: _score_duplicated_code,
}


def score_all_smells(source_code: str) -> dict[SmellType, SmellSignal | None]:
    """Return one slot per in-scope smell (None when that smell's heuristic did
    not trigger).

    Used by the multi-detector's phase 2, which needs an explicit "no evidence"
    result per smell to inform phase 3's LLM prompts — not just the winners.
    """
    tree = ast.parse(source_code)
    return {smell: scorer(tree) for smell, scorer in _SCORERS_BY_SMELL.items()}
