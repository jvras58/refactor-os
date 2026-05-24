"""Evaluation harness — measures each agent of the pipeline independently.

Three focused evaluations, one per agent, exactly as required by the course rubric:

* ``evaluate_detector``  — Agente Rastreador: confusion matrix over smelly + clean code,
  surfacing **Falsos Negativos** (deixou passar) e **Falsos Positivos** (viu onde não há).
* ``evaluate_refactor``  — Agente Refatorador: precisão/qualidade da solução proposta para
  cada problema, via checagens objetivas (pattern correto, sintaxe válida, API preservada).
* ``evaluate_critic``    — Agente Revisor: confiabilidade do julgamento, alimentando o Critic
  com soluções sabidamente corretas e incorretas (**false accept** e **false reject**).

``evaluate`` mantém o relatório combinado legado consumido por ``POST /api/v1/evaluate``.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from app.core.config import get_settings
from app.core.schemas import (
    BadSmellType,
    ConfusionMatrix,
    CriticMetrics,
    CriticTruthEntry,
    DetectorMetrics,
    EvaluationMetrics,
    FullEvaluationReport,
    GroundTruthEntry,
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

    # -------------------------------------------------------------- 1. Detector
    async def evaluate_detector(self) -> DetectorMetrics:
        """Confusion matrix of the Detector over smelly and clean programs.

        Positive class = "the file contains an in-scope bad smell".
        """
        ground_truth = self._load_ground_truth()
        cm = ConfusionMatrix()
        type_hits = type_total = 0
        per_file: list[dict] = []

        for entry in ground_truth:
            source_path = self._dataset_dir / entry.file
            if not source_path.is_file():
                logger.warning("dataset file missing: %s", source_path)
                continue
            expected_has_smell = entry.smell_type != BadSmellType.NO_SMELL

            try:
                detection = await self._service.detect(self._read(entry.file))
                predicted_has_smell = bool(detection.has_smell)
                detected_smell = detection.smell_type.value
            except Exception:
                logger.exception("Detector failed on %s", entry.file)
                per_file.append(
                    {"file": entry.file, "expected_smell": entry.smell_type.value, "error": True}
                )
                continue

            if expected_has_smell and predicted_has_smell:
                label = "TP"
                cm.true_positive += 1
                type_total += 1
                if detection.smell_type == entry.smell_type:
                    type_hits += 1
            elif expected_has_smell and not predicted_has_smell:
                label = "FN"  # deixou passar um smell real
                cm.false_negative += 1
            elif not expected_has_smell and predicted_has_smell:
                label = "FP"  # apontou smell em código limpo
                cm.false_positive += 1
            else:
                label = "TN"
                cm.true_negative += 1

            per_file.append(
                {
                    "file": entry.file,
                    "expected_smell": entry.smell_type.value,
                    "detected_smell": detected_smell,
                    "expected_has_smell": expected_has_smell,
                    "predicted_has_smell": predicted_has_smell,
                    "type_correct": detection.smell_type == entry.smell_type if expected_has_smell else None,
                    "classification": label,
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

    # ------------------------------------------------------------- 2. Refactor
    async def evaluate_refactor(self) -> RefactorQualityMetrics:
        """Precision/quality of the Recommender's solution for each detected problem."""
        problems = [e for e in self._load_ground_truth() if e.smell_type != BadSmellType.NO_SMELL]
        per_file: list[dict] = []
        correct = pattern_ok = syntax_ok = logic_ok = approved = 0
        iterations_sum = 0

        for entry in problems:
            source_path = self._dataset_dir / entry.file
            if not source_path.is_file():
                logger.warning("dataset file missing: %s", source_path)
                continue
            original = self._read(entry.file)
            try:
                result = await self._service.run(
                    RefactorRequest(source_code=original, file_name=entry.file)
                )
            except Exception:
                logger.exception("Pipeline failed on %s", entry.file)
                per_file.append({"file": entry.file, "error": True})
                continue

            iterations_sum += result.iterations
            if result.approved:
                approved += 1

            if result.proposal is None:
                per_file.append(
                    {
                        "file": entry.file,
                        "expected_pattern": entry.expected_pattern.value,
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
                entry.expected_pattern,
            )
            pattern_ok += assessment["pattern_correct"]
            syntax_ok += assessment["syntax_valid"]
            logic_ok += assessment["logic_preserved"]
            correct += assessment["is_correct"]

            per_file.append(
                {
                    "file": entry.file,
                    "expected_pattern": entry.expected_pattern.value,
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

        total = len(problems)
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

    # --------------------------------------------------------------- 3. Critic
    async def evaluate_critic(self) -> CriticMetrics:
        """Reliability of the Critic, fed with known-correct and known-incorrect solutions.

        Positive class = "the solution is correct" (the Critic ought to approve).
        """
        entries = self._load_critic_truth()
        cm = ConfusionMatrix()
        per_file: list[dict] = []

        for entry in entries:
            try:
                original = self._read(entry.problem_file)
                refactored = self._read(entry.solution_file)
            except FileNotFoundError:
                logger.warning("critic fixture missing: %s / %s", entry.problem_file, entry.solution_file)
                continue

            proposal = RefactoringProposal(
                applied_pattern=entry.applied_pattern,
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
                    logger.warning("Critic attempt %s failed on %s", attempt + 1, entry.solution_file)
            if review is None:
                logger.error("Critic failed on %s after retries", entry.solution_file)
                per_file.append({"solution_file": entry.solution_file, "error": True})
                continue
            predicted_approved = bool(review.is_approved)

            expected = entry.expected_approved
            if expected and predicted_approved:
                label = "TP"
                cm.true_positive += 1
            elif expected and not predicted_approved:
                label = "FN (false reject)"  # solução correta reprovada
                cm.false_negative += 1
            elif not expected and predicted_approved:
                label = "FP (false accept)"  # solução incorreta aprovada
                cm.false_positive += 1
            else:
                label = "TN"
                cm.true_negative += 1

            per_file.append(
                {
                    "solution_file": entry.solution_file,
                    "expected_approved": expected,
                    "predicted_approved": predicted_approved,
                    "defect_kind": entry.defect_kind,
                    "classification": label,
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
    async def evaluate_all(self) -> FullEvaluationReport:
        return FullEvaluationReport(
            detector=await self.evaluate_detector(),
            refactor=await self.evaluate_refactor(),
            critic=await self.evaluate_critic(),
        )

    async def evaluate(self) -> EvaluationMetrics:
        """Legacy combined report kept for backward compatibility with the dashboard/API."""
        detector = await self.evaluate_detector()
        refactor = await self.evaluate_refactor()
        return EvaluationMetrics(
            total=detector.total,
            detector_precision=detector.precision,
            detector_recall=detector.recall,
            refactor_accuracy=refactor.accuracy,
            per_file=detector.per_file,
        )
