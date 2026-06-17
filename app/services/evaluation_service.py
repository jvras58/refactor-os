"""Evaluation harness — measures each agent of the pipeline independently.

Three focused evaluations, one per agent, exactly as required by the course rubric:

* ``evaluate_detector``  — Agente Rastreador: avaliação multi-label sobre pares
  (arquivo, tipo) — cada arquivo gera 8 decisões binárias (4 smells + 4 patterns),
  comparadas contra ``ground_truth_detector.json``. Surface **Falsos Negativos**
  (deixou passar) e **Falsos Positivos** (viu onde não há).
* ``evaluate_refactor``  — Agente Refatorador: precisão/qualidade da solução proposta
  para cada problema, via checagens objetivas (pattern correto, sintaxe válida, API
  preservada). O pattern esperado é derivado dos ``problems`` do ground truth.
* ``evaluate_critic``    — Agente Revisor: confiabilidade do julgamento, alimentando o
  Critic com soluções sabidamente corretas e incorretas (**false accept** e **false
  reject**). O dataset atual não traz soluções rotuladas, então exige ``samples``.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from app.core.config import get_settings
from app.core.exceptions import InvalidPythonCodeError
from app.core.schemas import (
    ALL_TYPE_NAMES,
    SMELL_TO_PATTERN,
    ConfusionMatrix,
    CriticEvalSample,
    CriticMetrics,
    DetectorEvalSample,
    DetectorMetrics,
    FullEvaluationReport,
    GroundTruthEntry,
    PatternType,
    RefactorEvalSample,
    RefactoringProposal,
    RefactorQualityMetrics,
    RefactorRequest,
    SmellType,
)
from app.services.quality_checks import assess_refactoring
from app.services.refactor_service import RefactorService

logger = logging.getLogger(__name__)

_SMELL_VALUES = {smell.value for smell in SmellType}
_PATTERN_VALUES = {pattern.value for pattern in PatternType}


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

    @property
    def _examples_dir(self) -> Path:
        return self._dataset_dir / "examples"

    def _load_ground_truth(self) -> list[GroundTruthEntry]:
        path = self._dataset_dir / "ground_truth_detector.json"
        raw = json.loads(path.read_text(encoding="utf-8"))
        return [GroundTruthEntry(**entry) for entry in raw]

    def _read_example(self, relative: str) -> str:
        return (self._examples_dir / relative).read_text(encoding="utf-8")

    # ------------------------------------------------------------------ inputs
    def _detector_inputs_from_dataset(self) -> list[tuple[str, str, set[str]]]:
        """Yield ``(label, source_code, expected_problems)`` from the ground truth."""
        out: list[tuple[str, str, set[str]]] = []
        for entry in self._load_ground_truth():
            source_path = self._examples_dir / entry.file
            if not source_path.is_file():
                logger.warning("dataset file missing: %s", source_path)
                continue
            out.append((entry.file, self._read_example(entry.file), set(entry.problems)))
        return out

    @staticmethod
    def _detector_inputs_from_samples(
        samples: list[DetectorEvalSample],
    ) -> list[tuple[str, str, set[str]]]:
        return [
            (s.name or f"sample_{i + 1}", s.source_code, set(s.expected_problems))
            for i, s in enumerate(samples)
        ]

    # -------------------------------------------------------------- 1. Detector
    async def evaluate_detector(
        self, samples: list[DetectorEvalSample] | None = None
    ) -> DetectorMetrics:
        """Multi-label confusion matrix of the Detector over (file, type) pairs.

        Every file yields one binary decision per in-scope smell/pattern type.
        When ``samples`` is provided, evaluates over user-submitted code instead
        of the dataset.
        """
        inputs = (
            self._detector_inputs_from_samples(samples)
            if samples
            else self._detector_inputs_from_dataset()
        )
        cm = ConfusionMatrix()
        exact_matches = evaluated_files = 0
        per_file: list[dict] = []

        for label, source_code, expected in inputs:
            try:
                scan = await self._service.detect(source_code)
                detected = set(scan.detected_names())
            except InvalidPythonCodeError as exc:
                logger.warning("Detector rejected %s: %s", label, exc)
                per_file.append(
                    {"file": label, "expected_problems": sorted(expected), "error": str(exc)}
                )
                continue
            except Exception:
                logger.exception("Detector failed on %s", label)
                per_file.append(
                    {"file": label, "expected_problems": sorted(expected), "error": True}
                )
                continue

            evaluated_files += 1
            for type_name in ALL_TYPE_NAMES:
                expected_here = type_name in expected
                detected_here = type_name in detected
                if expected_here and detected_here:
                    cm.true_positive += 1
                elif expected_here and not detected_here:
                    cm.false_negative += 1  # deixou passar um problema real
                elif not expected_here and detected_here:
                    cm.false_positive += 1  # apontou problema onde não existe
                else:
                    cm.true_negative += 1

            exact = detected == expected
            exact_matches += exact
            per_file.append(
                {
                    "file": label,
                    "expected_problems": sorted(expected),
                    "detected_problems": sorted(detected),
                    "missing": sorted(expected - detected),
                    "extra": sorted(detected - expected),
                    "exact_match": exact,
                }
            )

        precision = _safe_div(cm.true_positive, cm.true_positive + cm.false_positive)
        recall = _safe_div(cm.true_positive, cm.true_positive + cm.false_negative)
        accuracy = _safe_div(cm.true_positive + cm.true_negative, cm.total)
        specificity = _safe_div(cm.true_negative, cm.true_negative + cm.false_positive)
        return DetectorMetrics(
            total_files=len(inputs),
            confusion=cm,
            precision=precision,
            recall=recall,
            accuracy=accuracy,
            f1=_f1(precision, recall),
            specificity=specificity,
            false_positive_rate=_safe_div(cm.false_positive, cm.false_positive + cm.true_negative),
            false_negative_rate=_safe_div(cm.false_negative, cm.false_negative + cm.true_positive),
            exact_match_rate=_safe_div(exact_matches, evaluated_files),
            per_file=per_file,
        )

    @staticmethod
    def _expected_pattern_from_problems(problems: list[str]) -> PatternType | None:
        """Derives the pattern the Recommender ought to apply for an example.

        The ground truth lists patterns explicitly when applicable; otherwise the
        pattern comes from the canonical smell → pattern mapping.
        """
        patterns = [PatternType(p) for p in problems if p in _PATTERN_VALUES]
        if patterns:
            return patterns[0]
        smells = [SmellType(p) for p in problems if p in _SMELL_VALUES]
        if smells:
            return SMELL_TO_PATTERN[smells[0]]
        return None

    def _refactor_inputs_from_dataset(self) -> list[tuple[str, str, PatternType]]:
        out: list[tuple[str, str, PatternType]] = []
        for entry in self._load_ground_truth():
            expected_pattern = self._expected_pattern_from_problems(entry.problems)
            if expected_pattern is None:  # arquivo limpo — não é alvo do Refatorador
                continue
            source_path = self._examples_dir / entry.file
            if not source_path.is_file():
                logger.warning("dataset file missing: %s", source_path)
                continue
            out.append((entry.file, self._read_example(entry.file), expected_pattern))
        return out

    @staticmethod
    def _refactor_inputs_from_samples(
        samples: list[RefactorEvalSample],
    ) -> list[tuple[str, str, PatternType]]:
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
        dataset. Each submitted sample is assumed to be a problem (no clean-file filter).
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
                        "detected_problems": result.detected_problems,
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
                    "detected_problems": result.detected_problems,
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

    @staticmethod
    def _critic_inputs_from_samples(
        samples: list[CriticEvalSample],
    ) -> list[tuple[str, str, str, PatternType, bool, str | None]]:
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

        Positive class = "the solution is correct" (the Critic ought to approve).
        The current dataset carries no labeled solutions, so ``samples`` is required.
        """
        if not samples:
            raise FileNotFoundError(
                "O dataset atual não possui soluções rotuladas para o Critic "
                "(critic_truth.json foi removido) — envie `samples` no body."
            )
        inputs = self._critic_inputs_from_samples(samples)
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
        """Roda as três avaliações. Detector e Refatorador caem no dataset quando a
        respectiva lista de samples é ``None``; o Critic exige ``critic_samples``
        (o dataset atual não traz soluções rotuladas)."""
        return FullEvaluationReport(
            detector=await self.evaluate_detector(samples=detector_samples),
            refactor=await self.evaluate_refactor(samples=refactor_samples),
            critic=await self.evaluate_critic(samples=critic_samples),
        )
