import json

import pytest

from app.core.schemas import BadSmellType, DesignPatternType, RefactoringProposal
from app.services.evaluation_service import EvaluationService


class FakeRefactorService:
    def __init__(self, responses: dict[BadSmellType, DesignPatternType]) -> None:
        self.responses = responses
        self.propose_calls = []

    async def propose(self, source_code, detection, prior_critique=None):
        self.propose_calls.append(
            {
                "source_code": source_code,
                "detection": detection,
                "prior_critique": prior_critique,
            }
        )
        return RefactoringProposal(
            applied_pattern=self.responses[detection.smell_type],
            refactored_code=source_code,
            architectural_explanation="fake proposal",
            expected_benefits=["testability"],
        )

    async def run(self, request):
        raise AssertionError("evaluate_recommender must call propose(), not run()")


def _write_dataset(tmp_path, entries):
    dataset_dir = tmp_path / "dataset"
    examples_dir = dataset_dir / "examples"
    examples_dir.mkdir(parents=True)
    (dataset_dir / "ground_truth.json").write_text(json.dumps(entries), encoding="utf-8")
    for entry in entries:
        (examples_dir / entry["file"]).write_text("def f():\n    return 1\n", encoding="utf-8")
    return dataset_dir


@pytest.mark.asyncio
async def test_evaluate_recommender_scores_pattern_matches(tmp_path):
    entries = [
        {
            "file": "01_complex_switch.py",
            "smell_type": "Complex/Long Switch Statements",
            "expected_pattern": "Strategy Pattern",
            "line_start": 1,
            "line_end": 3,
        },
        {
            "file": "02_long_parameter_list.py",
            "smell_type": "Long Parameter List",
            "expected_pattern": "Builder/Parameter Object",
            "line_start": 1,
            "line_end": 3,
        },
    ]
    dataset_dir = _write_dataset(tmp_path, entries)
    fake_service = FakeRefactorService(
        {
            BadSmellType.COMPLEX_SWITCH: DesignPatternType.STRATEGY,
            BadSmellType.LONG_PARAMETER: DesignPatternType.DEPENDENCY_INJECTION,
        }
    )
    service = EvaluationService(fake_service)
    service._settings.dataset_dir = dataset_dir

    metrics = await service.evaluate_recommender()

    assert metrics.total == 2
    assert metrics.correct == 1
    assert metrics.recommender_accuracy == 0.5
    assert len(metrics.per_file) == 2
    assert len(fake_service.propose_calls) == 2

    first = metrics.per_file[0]
    assert first.file == "01_complex_switch.py"
    assert first.expected_smell == BadSmellType.COMPLEX_SWITCH
    assert first.expected_pattern == DesignPatternType.STRATEGY
    assert first.applied_pattern == DesignPatternType.STRATEGY
    assert first.pattern_match is True
    assert first.error is None

    second = metrics.per_file[1]
    assert second.file == "02_long_parameter_list.py"
    assert second.expected_smell == BadSmellType.LONG_PARAMETER
    assert second.expected_pattern == DesignPatternType.BUILDER
    assert second.applied_pattern == DesignPatternType.DEPENDENCY_INJECTION
    assert second.pattern_match is False
    assert second.error is None


@pytest.mark.asyncio
async def test_evaluate_recommender_records_error_and_continues(tmp_path):
    dataset_dir = tmp_path / "dataset"
    examples_dir = dataset_dir / "examples"
    examples_dir.mkdir(parents=True)
    (dataset_dir / "ground_truth.json").write_text(
        json.dumps(
            [
                {
                    "file": "missing.py",
                    "smell_type": "Duplicated Code",
                    "expected_pattern": "Template Method",
                }
            ]
        ),
        encoding="utf-8",
    )
    fake_service = FakeRefactorService({})
    service = EvaluationService(fake_service)
    service._settings.dataset_dir = dataset_dir

    metrics = await service.evaluate_recommender()

    assert metrics.total == 1
    assert metrics.correct == 0
    assert metrics.recommender_accuracy == 0.0
    assert len(metrics.per_file) == 1
    assert metrics.per_file[0].file == "missing.py"
    assert metrics.per_file[0].expected_smell == BadSmellType.DUPLICATED_CODE
    assert metrics.per_file[0].expected_pattern == DesignPatternType.TEMPLATE_METHOD
    assert metrics.per_file[0].applied_pattern is None
    assert metrics.per_file[0].pattern_match is False
    assert "dataset file missing" in metrics.per_file[0].error
    assert fake_service.propose_calls == []
