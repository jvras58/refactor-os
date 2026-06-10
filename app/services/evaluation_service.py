"""Evaluation harness — measures each agent of the pipeline independently.

Three focused evaluations, one per agent, exactly as required by the course rubric:

* ``evaluate_detector``  — Agente Rastreador: confusion matrix over smelly + clean code,
  surfacing **Falsos Negativos** (deixou passar) e **Falsos Positivos** (viu onde não há).
* ``evaluate_refactor``  — Agente Refatorador: precisão/qualidade da solução proposta para
  cada problema, via checagens objetivas (pattern correto, sintaxe válida, API preservada).
* ``evaluate_critic``    — Agente Revisor: confiabilidade do julgamento, alimentando o Critic
  com soluções sabidamente corretas e incorretas (**false accept** e **false reject**).
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from app.core.config import get_settings
from app.core.schemas import (
    BadSmellType,
    ConfusionMatrix,
    CriticEvalSample,
    CriticMetrics,
    CriticTruthEntry,
    DesignPatternType,
    DetectorEvalSample,
    DetectorMetrics,
    FullEvaluationReport,
    GroundTruthEntry,
    RefactorEvalSample,
    RefactoringProposal,
    RefactorQualityMetrics,
    RefactorRequest,
)
from app.services.quality_checks import assess_refactoring
from app.services.refactor_service import RefactorService

logger = logging.getLogger(__name__)


def _safe_div(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def _f1(precision: float, recall: float) -> float:
    return _safe_div(2 * precision * recall, precision + recall)


class EvaluationService:
    """Runs the dataset and produces detector + refactoring + critic metrics."""

    def __init__(self, refactor_service: RefactorService | None = None) -> None:
        self._settings = get_settings()
        self._service = refactor_service or RefactorService()

    # ------------------------------------------------------------------ loaders
    @property
    def _dataset_dir(self) -> Path:
        return self._settings.dataset_dir

    def _load_ground_truth(self) -> list[GroundTruthEntry]:
        path = self._dataset_dir / "ground_truth.json"
        raw = json.loads(path.read_text(encoding="utf-8"))
        return [GroundTruthEntry(**entry) for entry in raw]

    def _load_critic_truth(self) -> list[CriticTruthEntry]:
        path = self._dataset_dir / "critic_truth.json"
        raw = json.loads(path.read_text(encoding="utf-8"))
        return [CriticTruthEntry(**entry) for entry in raw]

    def _read(self, relative: str) -> str:
        return (self._dataset_dir / relative).read_text(encoding="utf-8")

    # ------------------------------------------------------------------ inputs
    def _detector_inputs_from_dataset(self) -> list[tuple[str, str, BadSmellType]]:
        """Yield ``(label, source_code, expected_smell)`` tuples from ground_truth.json."""
        out: list[tuple[str, str, BadSmellType]] = []
        for entry in self._load_ground_truth():
            source_path = self._dataset_dir / entry.file
            if not source_path.is_file():
                logger.warning("dataset file missing: %s", source_path)
                continue
            out.append((entry.file, self._read(entry.file), entry.smell_type))
        return out

    @staticmethod
    def _detector_inputs_from_samples(
        samples: list[DetectorEvalSample],
    ) -> list[tuple[str, str, BadSmellType]]:
        return [
            (s.name or f"sample_{i + 1}", s.source_code, s.expected_smell)
            for i, s in enumerate(samples)
        ]

    # -------------------------------------------------------------- 1. Detector
    async def evaluate_detector(
        self, samples: list[DetectorEvalSample] | None = None
    ) -> DetectorMetrics:
        """Confusion matrix of the Detector over smelly and clean programs.

        Positive class = "the file contains an in-scope bad smell". When ``samples``
        is provided, evaluates over user-submitted code instead of the dataset.
        """
        inputs = (
            self._detector_inputs_from_samples(samples)
            if samples
            else self._detector_inputs_from_dataset()
        )
        cm = ConfusionMatrix()
        type_hits = type_total = 0
        per_file: list[dict] = []

        for label, source_code, expected_smell in inputs:
            expected_has_smell = expected_smell != BadSmellType.NO_SMELL

            try:
                detection = await self._service.detect(source_code)
                predicted_has_smell = bool(detection.has_smell)
                detected_smell = detection.smell_type.value
            except Exception:
                logger.exception("Detector failed on %s", label)
                per_file.append(
                    {"file": label, "expected_smell": expected_smell.value, "error": True}
                )
                continue

            if expected_has_smell and predicted_has_smell:
                classification = "TP"
                cm.true_positive += 1
                type_total += 1
                if detection.smell_type == expected_smell:
                    type_hits += 1
            elif expected_has_smell and not predicted_has_smell:
                classification = "FN"  # deixou passar um smell real
                cm.false_negative += 1
            elif not expected_has_smell and predicted_has_smell:
                classification = "FP"  # apontou smell em código limpo
                cm.false_positive += 1
            else:
                classification = "TN"
                cm.true_negative += 1

            per_file.append(
                {
                    "file": label,
                    "expected_smell": expected_smell.value,
                    "detected_smell": detected_smell,
                    "expected_has_smell": expected_has_smell,
                    "predicted_has_smell": predicted_has_smell,
                    "type_correct": detection.smell_type == expected_smell if expected_has_smell else None,
                    "classification": classification,
                }
            )

        precision = _safe_div(cm.true_positive, cm.true_positive + cm.false_positive)
        recall = _safe_div(cm.true_positive, cm.true_positive + cm.false_negative)
        accuracy = _safe_div(cm.true_positive + cm.true_negative, cm.total)
        specificity = _safe_div(cm.true_negative, cm.true_negative + cm.false_positive)
        return DetectorMetrics(
            total=cm.total,
            confusion=cm,
            precision=precision,
            recall=recall,
            accuracy=accuracy,
            f1=_f1(precision, recall),
            specificity=specificity,
            false_positive_rate=_safe_div(cm.false_positive, cm.false_positive + cm.true_negative),
            false_negative_rate=_safe_div(cm.false_negative, cm.false_negative + cm.true_positive),
            type_accuracy=_safe_div(type_hits, type_total),
            per_file=per_file,
        )

    def _refactor_inputs_from_dataset(self) -> list[tuple[str, str, DesignPatternType]]:
        out: list[tuple[str, str, DesignPatternType]] = []
        for entry in self._load_ground_truth():
            if entry.smell_type == BadSmellType.NO_SMELL:
                continue
            source_path = self._dataset_dir / entry.file
            if not source_path.is_file():
                logger.warning("dataset file missing: %s", source_path)
                continue
            out.append((entry.file, self._read(entry.file), entry.expected_pattern))
        return out

    @staticmethod
    def _refactor_inputs_from_samples(
        samples: list[RefactorEvalSample],
    ) -> list[tuple[str, str, DesignPatternType]]:
        return [
            (s.name or f"sample_{i + 1}", s.source_code, s.expected_pattern)
            for i, s in enumerate(samples)
        ]

    # ------------------------------------------------------------- 2. Refactor
    async def evaluate_refactor(
        self, samples: list[RefactorEvalSample] | None = None
    ) -> RefactorQualityMetrics:
        """Precision/quality of the Recommender's solution for each detected problem.

        When ``samples`` is provided, evaluates over user-submitted code instead of the
        dataset. Each submitted sample is assumed to be a problem (no NO_SMELL filter).
        """
        inputs = (
            self._refactor_inputs_from_samples(samples)
            if samples
            else self._refactor_inputs_from_dataset()
        )
        per_file: list[dict] = []
        correct = pattern_ok = syntax_ok = logic_ok = approved = 0
        iterations_sum = 0

        for label, original, expected_pattern in inputs:
            try:
                result = await self._service.run(
                    RefactorRequest(source_code=original, file_name=label)
                )
            except Exception:
                logger.exception("Pipeline failed on %s", label)
                per_file.append({"file": label, "error": True})
                continue

            iterations_sum += result.iterations
            if result.approved:
                approved += 1

            if result.proposal is None:
                per_file.append(
                    {
                        "file": label,
                        "expected_pattern": expected_pattern.value,
                        "applied_pattern": None,
                        "pattern_correct": False,
                        "syntax_valid": False,
                        "logic_preserved": False,
                        "is_correct": False,
                        "approved": result.approved,
                        "iterations": result.iterations,
                    }
                )
                continue

            assessment = assess_refactoring(
                original,
                result.proposal.refactored_code,
                result.proposal.applied_pattern,
                expected_pattern,
            )
            pattern_ok += assessment["pattern_correct"]
            syntax_ok += assessment["syntax_valid"]
            logic_ok += assessment["logic_preserved"]
            correct += assessment["is_correct"]

            per_file.append(
                {
                    "file": label,
                    "expected_pattern": expected_pattern.value,
                    "applied_pattern": result.proposal.applied_pattern.value,
                    "pattern_correct": assessment["pattern_correct"],
                    "syntax_valid": assessment["syntax_valid"],
                    "logic_preserved": assessment["logic_preserved"],
                    "missing_public_api": assessment["api_detail"].get("missing", []),
                    "is_correct": assessment["is_correct"],
                    "approved": result.approved,
                    "iterations": result.iterations,
                }
            )

        total = len(inputs)
        return RefactorQualityMetrics(
            total=total,
            accuracy=_safe_div(correct, total),
            pattern_accuracy=_safe_div(pattern_ok, total),
            syntax_valid_rate=_safe_div(syntax_ok, total),
            logic_preserved_rate=_safe_div(logic_ok, total),
            pipeline_approved_rate=_safe_div(approved, total),
            avg_iterations=_safe_div(iterations_sum, total),
            per_file=per_file,
        )

    def _critic_inputs_from_dataset(
        self,
    ) -> list[tuple[str, str, str, DesignPatternType, bool, str | None]]:
        """Yield ``(label, problem_code, solution_code, applied_pattern, expected, defect)``."""
        out: list[tuple[str, str, str, DesignPatternType, bool, str | None]] = []
        for entry in self._load_critic_truth():
            try:
                original = self._read(entry.problem_file)
                refactored = self._read(entry.solution_file)
            except FileNotFoundError:
                logger.warning(
                    "critic fixture missing: %s / %s", entry.problem_file, entry.solution_file
                )
                continue
            out.append(
                (
                    entry.solution_file,
                    original,
                    refactored,
                    entry.applied_pattern,
                    entry.expected_approved,
                    entry.defect_kind,
                )
            )
        return out

    @staticmethod
    def _critic_inputs_from_samples(
        samples: list[CriticEvalSample],
    ) -> list[tuple[str, str, str, DesignPatternType, bool, str | None]]:
        return [
            (
                s.name or f"sample_{i + 1}",
                s.problem_code,
                s.solution_code,
                s.applied_pattern,
                s.expected_approved,
                s.defect_kind,
            )
            for i, s in enumerate(samples)
        ]

    # --------------------------------------------------------------- 3. Critic
    async def evaluate_critic(
        self, samples: list[CriticEvalSample] | None = None
    ) -> CriticMetrics:
        """Reliability of the Critic, fed with known-correct and known-incorrect solutions.

        Positive class = "the solution is correct" (the Critic ought to approve). When
        ``samples`` is provided, evaluates over user-submitted code instead of the dataset.
        """
        inputs = (
            self._critic_inputs_from_samples(samples)
            if samples
            else self._critic_inputs_from_dataset()
        )
        cm = ConfusionMatrix()
        per_file: list[dict] = []

        for label, original, refactored, applied_pattern, expected, defect_kind in inputs:
            proposal = RefactoringProposal(
                applied_pattern=applied_pattern,
                refactored_code=refactored,
                architectural_explanation="(fixture de avaliação do Critic)",
                expected_benefits=["fixture"],
            )
            # O parser estruturado do Mistral ocasionalmente devolve texto puro em entradas
            # longas; uma re-tentativa no harness recupera essa falha transitória sem
            # interferir no veredito em si.
            review = None
            for attempt in range(2):
                try:
                    review = await self._service.review(original, proposal)
                    break
                except Exception:
                    logger.warning("Critic attempt %s failed on %s", attempt + 1, label)
            if review is None:
                logger.error("Critic failed on %s after retries", label)
                per_file.append({"solution_file": label, "error": True})
                continue
            predicted_approved = bool(review.is_approved)

            if expected and predicted_approved:
                classification = "TP"
                cm.true_positive += 1
            elif expected and not predicted_approved:
                classification = "FN (false reject)"  # solução correta reprovada
                cm.false_negative += 1
            elif not expected and predicted_approved:
                classification = "FP (false accept)"  # solução incorreta aprovada
                cm.false_positive += 1
            else:
                classification = "TN"
                cm.true_negative += 1

            per_file.append(
                {
                    "solution_file": label,
                    "expected_approved": expected,
                    "predicted_approved": predicted_approved,
                    "defect_kind": defect_kind,
                    "classification": classification,
                }
            )

        precision = _safe_div(cm.true_positive, cm.true_positive + cm.false_positive)
        recall = _safe_div(cm.true_positive, cm.true_positive + cm.false_negative)
        accuracy = _safe_div(cm.true_positive + cm.true_negative, cm.total)
        return CriticMetrics(
            total=cm.total,
            confusion=cm,
            accuracy=accuracy,
            precision=precision,
            recall=recall,
            f1=_f1(precision, recall),
            false_accept_rate=_safe_div(cm.false_positive, cm.false_positive + cm.true_negative),
            false_reject_rate=_safe_div(cm.false_negative, cm.false_negative + cm.true_positive),
            per_file=per_file,
        )

    # ---------------------------------------------------------------- combined
    async def evaluate_all(
        self,
        detector_samples: list[DetectorEvalSample] | None = None,
        refactor_samples: list[RefactorEvalSample] | None = None,
        critic_samples: list[CriticEvalSample] | None = None,
    ) -> FullEvaluationReport:
        """Roda as três avaliações. Cada lista de samples é independente: ``None``
        deixa o respectivo agente cair no dataset; lista preenchida ativa o modo
        ad-hoc só para aquele agente."""
        return FullEvaluationReport(
            detector=await self.evaluate_detector(samples=detector_samples),
            refactor=await self.evaluate_refactor(samples=refactor_samples),
            critic=await self.evaluate_critic(samples=critic_samples),
        )
