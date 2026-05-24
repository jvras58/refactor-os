import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DATASET_DIR = ROOT / "dataset"
EXAMPLES_DIR = DATASET_DIR / "examples"
GROUND_TRUTH_PATH = DATASET_DIR / "ground_truth.json"

EXPECTED_SMELLS = {
    "Complex/Long Switch Statements",
    "Long Parameter List",
    "God Class",
    "Tight Coupling",
    "Duplicated Code",
}

EXPECTED_PATTERNS = {
    "Strategy Pattern",
    "Builder/Parameter Object",
    "Facade/SRP",
    "Dependency Injection",
    "Template Method",
}


def _load_ground_truth() -> list[dict]:
    return json.loads(GROUND_TRUTH_PATH.read_text(encoding="utf-8"))


def test_ground_truth_has_expected_size_and_distribution():
    entries = _load_ground_truth()

    assert len(entries) == 20
    assert Counter(entry["smell_type"] for entry in entries) == {smell: 4 for smell in EXPECTED_SMELLS}
    assert Counter(entry["expected_pattern"] for entry in entries) == {
        pattern: 4 for pattern in EXPECTED_PATTERNS
    }


def test_ground_truth_references_existing_files_and_valid_line_ranges():
    entries = _load_ground_truth()

    for entry in entries:
        example_path = EXAMPLES_DIR / entry["file"]
        assert example_path.exists(), f"missing dataset example: {entry['file']}"

        line_start = entry["line_start"]
        line_end = entry["line_end"]
        total_lines = len(example_path.read_text(encoding="utf-8").splitlines())

        assert isinstance(line_start, int), entry["file"]
        assert isinstance(line_end, int), entry["file"]
        assert line_start >= 1, entry["file"]
        assert line_start <= line_end, entry["file"]
        assert line_end <= total_lines, entry["file"]


def test_new_examples_start_with_expected_docstring():
    entries = _load_ground_truth()
    new_files = {entry["file"] for entry in entries if entry["file"][:2].isdigit() and int(entry["file"][:2]) >= 6}

    assert len(new_files) == 15
    for filename in new_files:
        first_line = (EXAMPLES_DIR / filename).read_text(encoding="utf-8").splitlines()[0]
        assert first_line.startswith('"""Bad smell:'), filename
        assert "Bad smell:" in first_line, filename
        assert "esperado:" in first_line, filename
