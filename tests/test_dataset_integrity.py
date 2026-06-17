"""Integrity checks for the evaluation dataset (no LLM, no network)."""
from __future__ import annotations

import ast

from app.core.schemas import ALL_TYPE_NAMES, GroundTruthEntry


def _entries(read_dataset_json) -> list[GroundTruthEntry]:
    return [
        GroundTruthEntry(**entry)
        for entry in read_dataset_json("ground_truth_detector.json")
    ]


def test_ground_truth_files_exist(read_dataset_json, dataset_root):
    entries = _entries(read_dataset_json)
    assert entries, "ground_truth_detector.json não pode estar vazio"
    for entry in entries:
        assert (dataset_root / "examples" / entry.file).is_file(), f"missing {entry.file}"


def test_ground_truth_problems_use_known_type_names(read_dataset_json):
    known = set(ALL_TYPE_NAMES)
    for entry in _entries(read_dataset_json):
        unknown = set(entry.problems) - known
        assert not unknown, f"{entry.file}: tipos fora do escopo {unknown}"


def test_ground_truth_has_clean_and_smelly_examples(read_dataset_json):
    entries = _entries(read_dataset_json)
    clean = [e for e in entries if not e.problems]
    smelly = [e for e in entries if e.problems]
    assert clean, "esperava ao menos um exemplo limpo (problems=[])"
    assert smelly, "esperava exemplos com problemas rotulados"


def test_all_example_files_parse(dataset_root):
    examples = sorted((dataset_root / "examples").rglob("*.py"))
    assert examples, "dataset/examples não pode estar vazio"
    for path in examples:
        ast.parse(path.read_text(encoding="utf-8"))
