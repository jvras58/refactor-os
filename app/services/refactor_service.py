"""Orchestrates the deterministic Detector → Recommender → Critic pipeline.

Drives the explicit reflection loop (up to N iterations) outside the Team abstraction
so the academic evaluation can measure each stage independently.

Tool results (AST, pattern registry, syntax, diff) are pre-computed here and injected
into each agent's prompt. This avoids the Groq limitation that prevents combining
json_mode (output_schema) with tool/function calling in the same request.
"""
from __future__ import annotations

import json
import logging
from typing import cast

from app.agents.critic_agent import build_critic_agent
from app.agents.detector_agent import build_detector_agent
from app.agents.recommender_agent import build_recommender_agent
from app.core.config import get_settings
from app.core.schemas import (
    SMELL_TO_PATTERN,
    BadSmellType,
    DesignPatternType,
    RefactoringProposal,
    RefactorRequest,
    RefactorResult,
    ReflectionReview,
    SmellDetection,
)
from app.tools.ast_tools import analyze_ast
from app.tools.diff_tools import generate_diff
from app.tools.pattern_registry import lookup_pattern
from app.tools.syntax_tools import check_syntax

logger = logging.getLogger(__name__)

_DETECT_FALLBACK = SmellDetection(
    has_smell=False,
    smell_type=BadSmellType.NO_SMELL,
    reasoning="Detector falhou — erro interno ao chamar o agente.",
)


class RefactorService:
    """High-level façade that runs the multi-agent refactoring pipeline."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._detector = build_detector_agent()
        self._recommender = build_recommender_agent()
        self._critic = build_critic_agent()

    def detect(self, source_code: str) -> SmellDetection:
        ast_result = analyze_ast(source_code)
        prompt = (
            "Analise o seguinte código e retorne um SmellDetection.\n\n"
            "Resultados da análise AST (já executada):\n"
            f"```json\n{json.dumps(ast_result, indent=2, ensure_ascii=False)}\n```\n\n"
            f"Código-fonte:\n```python\n{source_code}\n```"
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
        pattern_info = lookup_pattern(expected.value)
        critique_block = (
            f"\n\nFeedback do Critic na rodada anterior (corrija obrigatoriamente):\n{prior_critique}"
            if prior_critique
            else ""
        )
        prompt = (
            f"Smell detectado: {detection.smell_type.value}\n"
            f"Pattern obrigatório: {expected.value}\n"
            f"Justificativa do Detector: {detection.reasoning}\n"
            f"Linhas afetadas: {detection.line_start}-{detection.line_end}\n\n"
            "Estrutura canônica do pattern (já consultada no registro):\n"
            f"```json\n{json.dumps(pattern_info, indent=2, ensure_ascii=False)}\n```\n\n"
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
        syntax = check_syntax(proposal.refactored_code)
        diff = generate_diff(source_code, proposal.refactored_code)
        prompt = (
            f"Pattern aplicado: {proposal.applied_pattern.value}\n\n"
            "Resultado de check_syntax (já executado):\n"
            f"```json\n{json.dumps(syntax, indent=2, ensure_ascii=False)}\n```\n\n"
            f"Diff original→refatorado (já gerado):\n```diff\n{diff}\n```\n\n"
            f"Código original:\n```python\n{source_code}\n```\n\n"
            f"Código refatorado:\n```python\n{proposal.refactored_code}\n```\n\n"
            "Avalie os 5 critérios das instruções e retorne ReflectionReview."
        )
        response = self._critic.run(prompt)
        return cast(ReflectionReview, response.content)

    def run(self, request: RefactorRequest) -> RefactorResult:
        try:
            detection = self.detect(request.source_code)
        except Exception:
            logger.exception("Detector stage failed")
            return RefactorResult(
                detection=_DETECT_FALLBACK,
                approved=False,
                iterations=0,
                error="Detector falhou — verifique logs para detalhes.",
            )

        if not detection.has_smell or detection.smell_type == BadSmellType.NO_SMELL:
            return RefactorResult(detection=detection, approved=False, iterations=0)

        proposal: RefactoringProposal | None = None
        review: ReflectionReview | None = None
        critique: str | None = None

        for iteration in range(1, self._settings.max_reflection_iterations + 1):
            logger.info("Reflection iteration %s", iteration)
            try:
                proposal = self.propose(request.source_code, detection, prior_critique=critique)
            except Exception:
                logger.exception("Recommender stage failed at iteration %s", iteration)
                return RefactorResult(
                    detection=detection,
                    proposal=proposal,
                    review=review,
                    iterations=iteration,
                    approved=False,
                    error=f"Recommender falhou na iteração {iteration} — verifique logs.",
                )

            try:
                review = self.review(request.source_code, proposal)
            except Exception:
                logger.exception("Critic stage failed at iteration %s", iteration)
                return RefactorResult(
                    detection=detection,
                    proposal=proposal,
                    review=review,
                    iterations=iteration,
                    approved=False,
                    error=f"Critic falhou na iteração {iteration} — verifique logs.",
                )

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
