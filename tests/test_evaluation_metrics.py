"""Deterministic tests for the metric math, using a scripted fake pipeline (no LLM)."""
from __future__ import annotations

import asyncio

from app.core.schemas import (
    BadSmellType,
    CriticEvalSample,
    DesignPatternType,
    DetectorEvalSample,
    RefactorEvalSample,
)


def test_detector_confusion_matrix(evaluation_service, write_text, write_json):
    write_text("p1.py", "GOD")  # smell -> detected: TP
    write_text("p2.py", "NONE")  # smell -> missed: FN
    write_text("c1.py", "NONE")  # clean -> clean: TN
    write_text("c2.py", "GOD")  # clean -> flagged: FP
    write_json(
        "ground_truth.json",
        [
            {"file": "p1.py", "smell_type": "God Class", "expected_pattern": "Facade/SRP"},
            {"file": "p2.py", "smell_type": "Long Parameter List", "expected_pattern": "Builder/Parameter Object"},
            {"file": "c1.py", "smell_type": "No Smell Detected", "expected_pattern": "None"},
            {"file": "c2.py", "smell_type": "No Smell Detected", "expected_pattern": "None"},
        ],
    )
    m = asyncio.run(evaluation_service.evaluate_detector())

    assert (m.confusion.true_positive, m.confusion.false_negative) == (1, 1)
    assert (m.confusion.false_positive, m.confusion.true_negative) == (1, 1)
    assert m.precision == 0.5
    assert m.recall == 0.5
    assert m.accuracy == 0.5
    assert m.specificity == 0.5
    assert m.false_positive_rate == 0.5
    assert m.false_negative_rate == 0.5
    assert m.type_accuracy == 1.0  # o único TP teve o tipo certo


def test_refactor_quality_metrics(evaluation_service, write_text, write_json):
    write_text("p1.py", "def alpha():\n    return 1\n")
    write_text("p2.py", "def beta():\n    return 2\n")
    write_json(
        "ground_truth.json",
        [
            {"file": "p1.py", "smell_type": "God Class", "expected_pattern": "Facade/SRP"},
            {"file": "p2.py", "smell_type": "Long Parameter List", "expected_pattern": "Builder/Parameter Object"},
        ],
    )
    m = asyncio.run(evaluation_service.evaluate_refactor())

    assert m.total == 2
    assert m.accuracy == 0.5  # só p1 totalmente correto
    assert m.pattern_accuracy == 0.5
    assert m.syntax_valid_rate == 1.0
    assert m.logic_preserved_rate == 0.5  # p2 perdeu a função pública 'beta'
    assert m.pipeline_approved_rate == 0.5
    assert m.avg_iterations == 2.0


def test_critic_confusion_matrix(evaluation_service, write_text, write_json):
    write_text("prob.py", "def x():\n    return 0\n")
    write_text("ok1.py", "APPROVE")  # correta, aprovada: TP
    write_text("ok2.py", "REJECT")  # correta, reprovada: FN
    write_text("bad1.py", "REJECT")  # incorreta, reprovada: TN
    write_text("bad2.py", "APPROVE")  # incorreta, aprovada: FP
    write_json(
        "critic_truth.json",
        [
            {"solution_file": "ok1.py", "problem_file": "prob.py", "applied_pattern": "Strategy Pattern", "expected_approved": True},
            {"solution_file": "ok2.py", "problem_file": "prob.py", "applied_pattern": "Strategy Pattern", "expected_approved": True},
            {"solution_file": "bad1.py", "problem_file": "prob.py", "applied_pattern": "Strategy Pattern", "expected_approved": False, "defect_kind": "logic"},
            {"solution_file": "bad2.py", "problem_file": "prob.py", "applied_pattern": "Strategy Pattern", "expected_approved": False, "defect_kind": "logic"},
        ],
    )
    m = asyncio.run(evaluation_service.evaluate_critic())

    assert (m.confusion.true_positive, m.confusion.false_negative) == (1, 1)
    assert (m.confusion.false_positive, m.confusion.true_negative) == (1, 1)
    assert m.false_accept_rate == 0.5  # 1 incorreta aprovada de 2 incorretas
    assert m.false_reject_rate == 0.5  # 1 correta reprovada de 2 corretas
    assert m.accuracy == 0.5


def test_detector_evaluates_submitted_samples(evaluation_service):
    samples = [
        DetectorEvalSample(source_code="GOD", expected_smell=BadSmellType.GOD_CLASS, name="ad-hoc-1"),
        DetectorEvalSample(source_code="NONE", expected_smell=BadSmellType.GOD_CLASS, name="ad-hoc-2"),
        DetectorEvalSample(source_code="NONE", expected_smell=BadSmellType.NO_SMELL, name="ad-hoc-3"),
        DetectorEvalSample(source_code="GOD", expected_smell=BadSmellType.NO_SMELL, name="ad-hoc-4"),
    ]
    m = asyncio.run(evaluation_service.evaluate_detector(samples=samples))

    assert (m.confusion.true_positive, m.confusion.false_negative) == (1, 1)
    assert (m.confusion.false_positive, m.confusion.true_negative) == (1, 1)
    assert {row["file"] for row in m.per_file} == {"ad-hoc-1", "ad-hoc-2", "ad-hoc-3", "ad-hoc-4"}
    assert m.precision == 0.5
    assert m.recall == 0.5


def test_refactor_evaluates_submitted_samples(evaluation_service):
    samples = [
        RefactorEvalSample(
            source_code="def alpha():\n    return 1\n",
            expected_pattern=DesignPatternType.FACADE_SRP,
            name="p1.py",
        ),
        RefactorEvalSample(
            source_code="def beta():\n    return 2\n",
            expected_pattern=DesignPatternType.BUILDER,
            name="p2.py",
        ),
    ]
    m = asyncio.run(evaluation_service.evaluate_refactor(samples=samples))

    assert m.total == 2
    assert m.accuracy == 0.5
    assert m.pattern_accuracy == 0.5
    assert m.syntax_valid_rate == 1.0


def test_critic_evaluates_submitted_samples(evaluation_service):
    samples = [
        CriticEvalSample(
            problem_code="def x():\n    return 0\n",
            solution_code="APPROVE",
            applied_pattern=DesignPatternType.STRATEGY,
            expected_approved=True,
            name="ok1",
        ),
        CriticEvalSample(
            problem_code="def x():\n    return 0\n",
            solution_code="REJECT",
            applied_pattern=DesignPatternType.STRATEGY,
            expected_approved=False,
            defect_kind="logic",
            name="bad1",
        ),
    ]
    m = asyncio.run(evaluation_service.evaluate_critic(samples=samples))

    assert m.total == 2
    assert m.confusion.true_positive == 1
    assert m.confusion.true_negative == 1
    assert m.accuracy == 1.0
    assert {row["solution_file"] for row in m.per_file} == {"ok1", "bad1"}


def test_evaluate_all_mixes_dataset_and_submitted_samples(evaluation_service, write_text, write_json):
    """Detector ad-hoc + Refatorador/Revisor dataset numa mesma chamada."""
    write_text("prob.py", "def x():\n    return 0\n")
    write_text("p1.py", "GOD")
    write_text("ok1.py", "APPROVE")
    write_json(
        "ground_truth.json",
        [{"file": "p1.py", "smell_type": "God Class", "expected_pattern": "Facade/SRP"}],
    )
    write_json(
        "critic_truth.json",
        [{
            "solution_file": "ok1.py",
            "problem_file": "prob.py",
            "applied_pattern": "Strategy Pattern",
            "expected_approved": True,
        }],
    )
    detector_samples = [
        DetectorEvalSample(source_code="GOD", expected_smell=BadSmellType.GOD_CLASS, name="ad-hoc"),
    ]

    report = asyncio.run(
        evaluation_service.evaluate_all(detector_samples=detector_samples)
    )

    assert report.detector.total == 1
    assert {row["file"] for row in report.detector.per_file} == {"ad-hoc"}
    assert report.refactor.total == 1
    assert {row["file"] for row in report.refactor.per_file} == {"p1.py"}
    assert report.critic.total == 1
    assert {row["solution_file"] for row in report.critic.per_file} == {"ok1.py"}


def test_evaluate_detector_dataset_path_still_works(evaluation_service, write_text, write_json):
    """Regressão: passar samples=None continua lendo ground_truth.json."""
    write_text("p1.py", "GOD")
    write_json(
        "ground_truth.json",
        [{"file": "p1.py", "smell_type": "God Class", "expected_pattern": "Facade/SRP"}],
    )
    m = asyncio.run(evaluation_service.evaluate_detector())
    assert m.confusion.true_positive == 1
