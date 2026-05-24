"""Deterministic tests for the metric math, using a scripted fake pipeline (no LLM)."""
from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

from app.core.schemas import (
    BadSmellType,
    DesignPatternType,
    RefactoringProposal,
    RefactorResult,
    ReflectionReview,
    SmellDetection,
)
from app.services.evaluation_service import EvaluationService


class FakeRefactorService:
    """Scripted stand-in: decisions keyed by sentinels in the source/solution."""

    async def detect(self, source_code: str) -> SmellDetection:
        if "GOD" in source_code:
            return SmellDetection(
                has_smell=True, smell_type=BadSmellType.GOD_CLASS, reasoning="fake"
            )
        return SmellDetection(has_smell=False, smell_type=BadSmellType.NO_SMELL, reasoning="fake")

    async def run(self, request) -> RefactorResult:
        detection = SmellDetection(has_smell=True, smell_type=BadSmellType.GOD_CLASS, reasoning="fake")
        if request.file_name == "p1.py":
            proposal = RefactoringProposal(
                applied_pattern=DesignPatternType.FACADE_SRP,
                refactored_code="def alpha():\n    return 1\n",
                architectural_explanation="fake",
                expected_benefits=["x"],
            )
            return RefactorResult(detection=detection, proposal=proposal, approved=True, iterations=1)
        proposal = RefactoringProposal(
            applied_pattern=DesignPatternType.STRATEGY,  # errado p/ Long Parameter
            refactored_code="def gamma():\n    return 2\n",  # perde 'beta'
            architectural_explanation="fake",
            expected_benefits=["x"],
        )
        return RefactorResult(detection=detection, proposal=proposal, approved=False, iterations=3)

    async def review(self, original: str, proposal: RefactoringProposal) -> ReflectionReview:
        approved = "APPROVE" in proposal.refactored_code
        return ReflectionReview(is_approved=approved, critique="fake")


def _service_with_dataset(tmp_path) -> EvaluationService:
    service = EvaluationService(FakeRefactorService())
    service._settings = SimpleNamespace(dataset_dir=tmp_path)
    return service


def test_detector_confusion_matrix(tmp_path):
    (tmp_path / "p1.py").write_text("GOD", encoding="utf-8")  # smell -> detected: TP
    (tmp_path / "p2.py").write_text("NONE", encoding="utf-8")  # smell -> missed: FN
    (tmp_path / "c1.py").write_text("NONE", encoding="utf-8")  # clean -> clean: TN
    (tmp_path / "c2.py").write_text("GOD", encoding="utf-8")  # clean -> flagged: FP
    (tmp_path / "ground_truth.json").write_text(
        json.dumps(
            [
                {"file": "p1.py", "smell_type": "God Class", "expected_pattern": "Facade/SRP"},
                {"file": "p2.py", "smell_type": "Long Parameter List", "expected_pattern": "Builder/Parameter Object"},
                {"file": "c1.py", "smell_type": "No Smell Detected", "expected_pattern": "None"},
                {"file": "c2.py", "smell_type": "No Smell Detected", "expected_pattern": "None"},
            ]
        ),
        encoding="utf-8",
    )
    m = asyncio.run(_service_with_dataset(tmp_path).evaluate_detector())

    assert (m.confusion.true_positive, m.confusion.false_negative) == (1, 1)
    assert (m.confusion.false_positive, m.confusion.true_negative) == (1, 1)
    assert m.precision == 0.5
    assert m.recall == 0.5
    assert m.accuracy == 0.5
    assert m.specificity == 0.5
    assert m.false_positive_rate == 0.5
    assert m.false_negative_rate == 0.5
    assert m.type_accuracy == 1.0  # o único TP teve o tipo certo


def test_refactor_quality_metrics(tmp_path):
    (tmp_path / "p1.py").write_text("def alpha():\n    return 1\n", encoding="utf-8")
    (tmp_path / "p2.py").write_text("def beta():\n    return 2\n", encoding="utf-8")
    (tmp_path / "ground_truth.json").write_text(
        json.dumps(
            [
                {"file": "p1.py", "smell_type": "God Class", "expected_pattern": "Facade/SRP"},
                {"file": "p2.py", "smell_type": "Long Parameter List", "expected_pattern": "Builder/Parameter Object"},
            ]
        ),
        encoding="utf-8",
    )
    m = asyncio.run(_service_with_dataset(tmp_path).evaluate_refactor())

    assert m.total == 2
    assert m.accuracy == 0.5  # só p1 totalmente correto
    assert m.pattern_accuracy == 0.5
    assert m.syntax_valid_rate == 1.0
    assert m.logic_preserved_rate == 0.5  # p2 perdeu a função pública 'beta'
    assert m.pipeline_approved_rate == 0.5
    assert m.avg_iterations == 2.0


def test_critic_confusion_matrix(tmp_path):
    (tmp_path / "prob.py").write_text("def x():\n    return 0\n", encoding="utf-8")
    (tmp_path / "ok1.py").write_text("APPROVE", encoding="utf-8")  # correta, aprovada: TP
    (tmp_path / "ok2.py").write_text("REJECT", encoding="utf-8")  # correta, reprovada: FN
    (tmp_path / "bad1.py").write_text("REJECT", encoding="utf-8")  # incorreta, reprovada: TN
    (tmp_path / "bad2.py").write_text("APPROVE", encoding="utf-8")  # incorreta, aprovada: FP
    (tmp_path / "critic_truth.json").write_text(
        json.dumps(
            [
                {"solution_file": "ok1.py", "problem_file": "prob.py", "applied_pattern": "Strategy Pattern", "expected_approved": True},
                {"solution_file": "ok2.py", "problem_file": "prob.py", "applied_pattern": "Strategy Pattern", "expected_approved": True},
                {"solution_file": "bad1.py", "problem_file": "prob.py", "applied_pattern": "Strategy Pattern", "expected_approved": False, "defect_kind": "logic"},
                {"solution_file": "bad2.py", "problem_file": "prob.py", "applied_pattern": "Strategy Pattern", "expected_approved": False, "defect_kind": "logic"},
            ]
        ),
        encoding="utf-8",
    )
    m = asyncio.run(_service_with_dataset(tmp_path).evaluate_critic())

    assert (m.confusion.true_positive, m.confusion.false_negative) == (1, 1)
    assert (m.confusion.false_positive, m.confusion.true_negative) == (1, 1)
    assert m.false_accept_rate == 0.5  # 1 incorreta aprovada de 2 incorretas
    assert m.false_reject_rate == 0.5  # 1 correta reprovada de 2 corretas
    assert m.accuracy == 0.5
