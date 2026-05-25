"""Integrity checks for the evaluation dataset (no LLM, no network)."""
from __future__ import annotations

import ast
import json
from pathlib import Path

from app.core.schemas import BadSmellType, CriticTruthEntry, GroundTruthEntry

DATASET = Path(__file__).resolve().parent.parent / "dataset"


def _load(name: str):
    return json.loads((DATASET / name).read_text(encoding="utf-8"))


def test_ground_truth_has_10_smelly_and_10_clean():
    entries = [GroundTruthEntry(**e) for e in _load("ground_truth.json")]
    smelly = [e for e in entries if e.smell_type != BadSmellType.NO_SMELL]
    clean = [e for e in entries if e.smell_type == BadSmellType.NO_SMELL]
    assert len(smelly) == 10
    assert len(clean) == 10
    for entry in entries:
        assert (DATASET / entry.file).is_file(), f"missing {entry.file}"


def test_critic_truth_has_10_correct_and_10_incorrect():
    entries = [CriticTruthEntry(**e) for e in _load("critic_truth.json")]
    correct = [e for e in entries if e.expected_approved]
    incorrect = [e for e in entries if not e.expected_approved]
    assert len(correct) == 10
    assert len(incorrect) == 10
    for entry in entries:
        assert (DATASET / entry.solution_file).is_file(), f"missing {entry.solution_file}"
        assert (DATASET / entry.problem_file).is_file(), f"missing {entry.problem_file}"
        if not entry.expected_approved:
            assert entry.defect_kind, f"incorrect solution {entry.solution_file} must declare defect_kind"


def test_smelly_examples_and_clean_files_parse_except_intentional_syntax_defects():
    # todos os exemplos e arquivos limpos devem ser Python válido
    for f in list(DATASET.glob("examples/*.py")) + list(DATASET.glob("clean/*.py")):
        ast.parse(f.read_text(encoding="utf-8"))
    for f in DATASET.glob("solutions/correct/*.py"):
        ast.parse(f.read_text(encoding="utf-8"))


def test_intentional_syntax_defects_do_not_parse():
    entries = [CriticTruthEntry(**e) for e in _load("critic_truth.json")]
    syntax_defects = [e for e in entries if e.defect_kind == "syntax"]
    assert syntax_defects, "esperava ao menos um defeito de sintaxe no conjunto incorreto"
    for entry in syntax_defects:
        src = (DATASET / entry.solution_file).read_text(encoding="utf-8")
        try:
            ast.parse(src)
            raise AssertionError(f"{entry.solution_file} deveria ter erro de sintaxe")
        except SyntaxError:
            pass
