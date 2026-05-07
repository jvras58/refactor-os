"""Evaluation harness — runs the dataset against the pipeline and computes metrics."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.core.schemas import (
    BadSmellType,
    EvaluationMetrics,
    GroundTruthEntry,
    RefactorRequest,
)
from app.services.refactor_service import RefactorService

logger = logging.getLogger(__name__)


def _load_ground_truth(path: Path) -> list[GroundTruthEntry]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [GroundTruthEntry(**entry) for entry in raw]


def _safe_div(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


class EvaluationService:
    """Runs the dataset and produces detector + refactoring metrics."""

    def __init__(self, refactor_service: RefactorService | None = None) -> None:
        self._settings = get_settings()
        self._service = refactor_service or RefactorService()

    def evaluate(self) -> EvaluationMetrics:
        dataset_dir = self._settings.dataset_dir
        ground_truth_path = dataset_dir / "ground_truth.json"
        examples_dir = dataset_dir / "examples"
        ground_truth = _load_ground_truth(ground_truth_path)

        per_file: list[dict[str, Any]] = []
        true_positive = false_positive = false_negative = 0
        approved_correct = 0

        for entry in ground_truth:
            source_path = examples_dir / entry.file
            if not source_path.is_file():
                logger.warning("dataset file missing: %s", source_path)
                continue
            source_code = source_path.read_text(encoding="utf-8")
            result = self._service.run(RefactorRequest(source_code=source_code, file_name=entry.file))

            expected_has_smell = entry.smell_type != BadSmellType.NO_SMELL
            detected = result.detection.has_smell and result.detection.smell_type == entry.smell_type

            if detected and expected_has_smell:
                true_positive += 1
            elif result.detection.has_smell and not detected:
                false_positive += 1
            elif not result.detection.has_smell and expected_has_smell:
                false_negative += 1

            pattern_match = (
                result.approved
                and result.proposal is not None
                and result.proposal.applied_pattern == entry.expected_pattern
            )
            if pattern_match:
                approved_correct += 1

            per_file.append(
                {
                    "file": entry.file,
                    "expected_smell": entry.smell_type.value,
                    "detected_smell": result.detection.smell_type.value,
                    "expected_pattern": entry.expected_pattern.value,
                    "applied_pattern": result.proposal.applied_pattern.value if result.proposal else None,
                    "approved": result.approved,
                    "iterations": result.iterations,
                    "smell_match": detected,
                    "pattern_match": pattern_match,
                }
            )

        total = len(ground_truth)
        precision = _safe_div(true_positive, true_positive + false_positive)
        recall = _safe_div(true_positive, true_positive + false_negative)
        accuracy = _safe_div(approved_correct, total)

        return EvaluationMetrics(
            total=total,
            detector_precision=precision,
            detector_recall=recall,
            refactor_accuracy=accuracy,
            per_file=per_file,
        )
