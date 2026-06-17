"""Deterministic tests for the metric math, using a scripted fake pipeline (no LLM)."""
from __future__ import annotations

import asyncio

import pytest

from app.core.schemas import (
    CriticEvalSample,
    DetectorEvalSample,
    PatternType,
    RefactorEvalSample,
)

_GOD = "God Class"
_FACADE = "Facade"
_SWITCH = "Complex/Long Switch Statements"
_STRATEGY = "Strategy Pattern"


def test_detector_multilabel_confusion_matrix(evaluation_service, write_example, write_json):
    # o fake detecta {God Class, Facade} quando o código contém "GOD" e nada caso contrário
    write_example("p1.py", "GOD")  # esperado {God, Facade} -> 2 TP + 6 TN, exato
    write_example("p2.py", "NONE")  # esperado {God, Facade} -> 2 FN + 6 TN
    write_example("c1.py", "NONE")  # esperado {} -> 8 TN, exato
    write_example("c2.py", "GOD")  # esperado {} -> 2 FP + 6 TN
    write_json(
        "ground_truth_detector.json",
        [
            {"file": "p1.py", "problems": [_GOD, _FACADE]},
            {"file": "p2.py", "problems": [_GOD, _FACADE]},
            {"file": "c1.py", "problems": []},
            {"file": "c2.py", "problems": []},
        ],
    )
    m = asyncio.run(evaluation_service.evaluate_detector())

    assert m.total_files == 4
    assert (m.confusion.true_positive, m.confusion.false_negative) == (2, 2)
    assert (m.confusion.false_positive, m.confusion.true_negative) == (2, 26)
    assert m.confusion.total == 32  # 4 arquivos × 8 tipos
    assert m.precision == 0.5
    assert m.recall == 0.5
    assert m.exact_match_rate == 0.5  # p1 e c1 exatos


def test_detector_invalid_python_is_reported_not_counted(
    evaluation_service, write_example, write_json
):
    write_example("ok.py", "GOD")
    write_example("broken.py", "BROKEN")  # fake levanta InvalidPythonCodeError
    write_json(
        "ground_truth_detector.json",
        [
            {"file": "ok.py", "problems": [_GOD, _FACADE]},
            {"file": "broken.py", "problems": [_GOD]},
        ],
    )
    m = asyncio.run(evaluation_service.evaluate_detector())

    assert m.total_files == 2
    assert m.confusion.total == 8  # só ok.py entra na matriz
    error_row = next(r for r in m.per_file if r["file"] == "broken.py")
    assert error_row["error"]
    assert m.exact_match_rate == 1.0  # entre os avaliados, ok.py foi exato


def test_refactor_quality_metrics(evaluation_service, write_example, write_json):
    write_example("p1.py", "def alpha():\n    return 1\n")
    write_example("p2.py", "def beta():\n    return 2\n")
    write_json(
        "ground_truth_detector.json",
        [
            {"file": "p1.py", "problems": [_GOD, _FACADE]},
            {"file": "p2.py", "problems": ["Long Parameter List", "Builder"]},
            {"file": "clean.py", "problems": []},  # limpo — fora do alvo do Refatorador
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


def test_refactor_expected_pattern_derived_from_smell_when_absent(
    evaluation_service, write_example, write_json
):
    """Entrada só com smell (sem pattern explícito) deriva o pattern canônico."""
    write_example("p1.py", "def alpha():\n    return 1\n")
    write_json(
        "ground_truth_detector.json",
        [{"file": "p1.py", "problems": [_GOD]}],  # sem "Facade" explícito
    )
    m = asyncio.run(evaluation_service.evaluate_refactor())

    assert m.total == 1
    assert m.per_file[0]["expected_pattern"] == _FACADE
    assert m.pattern_accuracy == 1.0  # fake aplica Facade em p1.py


def test_detector_evaluates_submitted_samples(evaluation_service):
    samples = [
        DetectorEvalSample(source_code="GOD", expected_problems=[_GOD, _FACADE], name="ad-hoc-1"),
        DetectorEvalSample(source_code="NONE", expected_problems=[_GOD, _FACADE], name="ad-hoc-2"),
        DetectorEvalSample(source_code="NONE", expected_problems=[], name="ad-hoc-3"),
        DetectorEvalSample(source_code="GOD", expected_problems=[], name="ad-hoc-4"),
    ]
    m = asyncio.run(evaluation_service.evaluate_detector(samples=samples))

    assert m.total_files == 4
    assert (m.confusion.true_positive, m.confusion.false_negative) == (2, 2)
    assert (m.confusion.false_positive, m.confusion.true_negative) == (2, 26)
    assert {row["file"] for row in m.per_file} == {"ad-hoc-1", "ad-hoc-2", "ad-hoc-3", "ad-hoc-4"}
    assert m.precision == 0.5
    assert m.recall == 0.5


def test_detector_sample_with_multiple_smells(evaluation_service):
    samples = [
        DetectorEvalSample(
            source_code="GOD SWITCH",
            expected_problems=[_GOD, _FACADE, _SWITCH, _STRATEGY],
            name="multi",
        ),
    ]
    m = asyncio.run(evaluation_service.evaluate_detector(samples=samples))

    assert m.confusion.true_positive == 4
    assert m.confusion.false_negative == 0
    assert m.exact_match_rate == 1.0


def test_refactor_evaluates_submitted_samples(evaluation_service):
    samples = [
        RefactorEvalSample(
            source_code="def alpha():\n    return 1\n",
            expected_pattern=PatternType.FACADE,
            name="p1.py",
        ),
        RefactorEvalSample(
            source_code="def beta():\n    return 2\n",
            expected_pattern=PatternType.BUILDER,
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
            applied_pattern=PatternType.STRATEGY,
            expected_approved=True,
            name="ok1",
        ),
        CriticEvalSample(
            problem_code="def x():\n    return 0\n",
            solution_code="REJECT",
            applied_pattern=PatternType.STRATEGY,
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


def test_critic_without_samples_raises(evaluation_service):
    with pytest.raises(FileNotFoundError):
        asyncio.run(evaluation_service.evaluate_critic())


def test_evaluate_all_mixes_dataset_and_submitted_samples(
    evaluation_service, write_example, write_json
):
    """Detector ad-hoc + Refatorador dataset + Critic ad-hoc numa mesma chamada."""
    write_example("p1.py", "GOD")
    write_json(
        "ground_truth_detector.json",
        [{"file": "p1.py", "problems": [_GOD, _FACADE]}],
    )
    detector_samples = [
        DetectorEvalSample(source_code="GOD", expected_problems=[_GOD, _FACADE], name="ad-hoc"),
    ]
    critic_samples = [
        CriticEvalSample(
            problem_code="def x():\n    return 0\n",
            solution_code="APPROVE",
            applied_pattern=PatternType.STRATEGY,
            expected_approved=True,
            name="ok1.py",
        ),
    ]

    report = asyncio.run(
        evaluation_service.evaluate_all(
            detector_samples=detector_samples, critic_samples=critic_samples
        )
    )

    assert report.detector.total_files == 1
    assert {row["file"] for row in report.detector.per_file} == {"ad-hoc"}
    assert report.refactor.total == 1
    assert {row["file"] for row in report.refactor.per_file} == {"p1.py"}
    assert report.critic.total == 1
    assert {row["solution_file"] for row in report.critic.per_file} == {"ok1.py"}


def test_evaluate_detector_dataset_path_still_works(
    evaluation_service, write_example, write_json
):
    """Regressão: passar samples=None continua lendo ground_truth_detector.json."""
    write_example("p1.py", "GOD")
    write_json(
        "ground_truth_detector.json",
        [{"file": "p1.py", "problems": [_GOD, _FACADE]}],
    )
    m = asyncio.run(evaluation_service.evaluate_detector())
    assert m.confusion.true_positive == 2
    assert m.exact_match_rate == 1.0
