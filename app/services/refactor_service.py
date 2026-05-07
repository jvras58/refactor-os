"""Orchestrates the deterministic Detector → Recommender → Critic pipeline.

Drives the explicit reflection loop (up to N iterations) outside the Team abstraction
so the academic evaluation can measure each stage independently.
"""
from __future__ import annotations

import logging
from typing import cast

from app.agents import (
    build_critic_agent,
    build_detector_agent,
    build_recommender_agent,
)
from app.core.config import get_settings
from app.core.schemas import (
    BadSmellType,
    DesignPatternType,
    RefactoringProposal,
    RefactorRequest,
    RefactorResult,
    ReflectionReview,
    SMELL_TO_PATTERN,
    SmellDetection,
)

logger = logging.getLogger(__name__)


class RefactorService:
    """High-level façade that runs the multi-agent refactoring pipeline."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._detector = build_detector_agent()
        self._recommender = build_recommender_agent()
        self._critic = build_critic_agent()

    def detect(self, source_code: str) -> SmellDetection:
        prompt = (
            "Analise o seguinte código e retorne um SmellDetection.\n"
            "```python\n" + source_code + "\n```"
        )
        response = self._detector.run(prompt)
        return cast(SmellDetection, response.content)

    def propose(
        self,
        source_code: str,
        detection: SmellDetection,
        prior_critique: str | None = None,
    ) -> RefactoringProposal:
        expected = SMELL_TO_PATTERN.get(detection.smell_type, DesignPatternType.NONE)
        critique_block = (
            f"\n\nFeedback do Critic na rodada anterior (corrija):\n{prior_critique}"
            if prior_critique
            else ""
        )
        prompt = (
            f"Smell detectado: {detection.smell_type.value}\n"
            f"Pattern obrigatório: {expected.value}\n"
            f"Justificativa do Detector: {detection.reasoning}\n"
            f"Linhas afetadas: {detection.line_start}-{detection.line_end}\n\n"
            f"Código original:\n```python\n{source_code}\n```"
            f"{critique_block}\n\n"
            "Retorne RefactoringProposal."
        )
        response = self._recommender.run(prompt)
        return cast(RefactoringProposal, response.content)

    def review(
        self,
        source_code: str,
        proposal: RefactoringProposal,
    ) -> ReflectionReview:
        prompt = (
            f"Pattern aplicado: {proposal.applied_pattern.value}\n\n"
            f"Código original:\n```python\n{source_code}\n```\n\n"
            f"Código refatorado:\n```python\n{proposal.refactored_code}\n```\n\n"
            "Valide sintaxe, preservação de lógica e correção do pattern. Retorne ReflectionReview."
        )
        response = self._critic.run(prompt)
        return cast(ReflectionReview, response.content)

    def run(self, request: RefactorRequest) -> RefactorResult:
        detection = self.detect(request.source_code)

        if not detection.has_smell or detection.smell_type == BadSmellType.NO_SMELL:
            return RefactorResult(detection=detection, approved=False, iterations=0)

        proposal: RefactoringProposal | None = None
        review: ReflectionReview | None = None
        critique: str | None = None

        for iteration in range(1, self._settings.max_reflection_iterations + 1):
            logger.info("Reflection iteration %s", iteration)
            proposal = self.propose(request.source_code, detection, prior_critique=critique)
            review = self.review(request.source_code, proposal)
            if review.is_approved:
                return RefactorResult(
                    detection=detection,
                    proposal=proposal,
                    review=review,
                    iterations=iteration,
                    approved=True,
                )
            critique = review.critique

        return RefactorResult(
            detection=detection,
            proposal=proposal,
            review=review,
            iterations=self._settings.max_reflection_iterations,
            approved=False,
        )
