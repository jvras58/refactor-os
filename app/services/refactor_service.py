"""Orchestrates the deterministic Detector → Recommender → Critic pipeline.

Drives the explicit reflection loop (up to N iterations) outside the Team abstraction
so the academic evaluation can measure each stage independently.

Each agent runs tools on the primary model (no json_mode) and delegates structured
output formatting to output_model — a separate Groq request with output_schema but
no tools. This resolves the Groq limitation that prevents combining tool/function
calling with JSON mode in a single request.
"""
from __future__ import annotations

import json
import logging
import re

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

logger = logging.getLogger(__name__)

_DETECT_FALLBACK = SmellDetection(
    has_smell=False,
    smell_type=BadSmellType.NO_SMELL,
    reasoning="Detector falhou — erro interno ao chamar o agente.",
)

_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)


def _extract_json(text: str) -> dict:
    """Fallback: extract and parse the first JSON object from a raw text response."""
    match = _JSON_BLOCK_RE.search(text)
    if match:
        return json.loads(match.group(1).strip())
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        return json.loads(text[start : end + 1])
    raise ValueError(f"Nenhum objeto JSON encontrado na resposta:\n{text[:500]}")


def _parse_response(content: object, model_class: type) -> object:
    """Return typed content: use Agno's parsed object or fall back to JSON extraction."""
    if isinstance(content, model_class):
        return content
    if isinstance(content, str):
        data = _extract_json(content)
        return model_class.model_validate(data)
    raise ValueError(f"Tipo inesperado retornado pelo agente: {type(content)} — {content!r}")


class RefactorService:
    """High-level façade that runs the multi-agent refactoring pipeline."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._detector = build_detector_agent()
        self._recommender = build_recommender_agent()
        self._critic = build_critic_agent()

    def detect(self, source_code: str) -> SmellDetection:
        prompt = (
            "Analise o seguinte código-fonte e retorne um SmellDetection.\n"
            "Use obrigatoriamente `ast_analyzer_tool` antes de concluir.\n\n"
            f"```python\n{source_code}\n```"
        )
        response = self._detector.run(prompt)
        return _parse_response(response.content, SmellDetection)

    def propose(
        self,
        source_code: str,
        detection: SmellDetection,
        prior_critique: str | None = None,
    ) -> RefactoringProposal:
        expected = SMELL_TO_PATTERN.get(detection.smell_type, DesignPatternType.NONE)
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
            "Use obrigatoriamente `design_pattern_reference_tool` para consultar a estrutura "
            "canônica do pattern antes de propor o código.\n\n"
            f"Código original:\n```python\n{source_code}\n```"
            f"{critique_block}\n\n"
            "Retorne RefactoringProposal. "
            "No campo `refactored_code` use apenas aspas simples ou duplas — nunca aspas triplas."
        )
        response = self._recommender.run(prompt)
        return _parse_response(response.content, RefactoringProposal)

    def review(
        self,
        source_code: str,
        proposal: RefactoringProposal,
    ) -> ReflectionReview:
        prompt = (
            f"Pattern aplicado: {proposal.applied_pattern.value}\n\n"
            "Use obrigatoriamente:\n"
            "1. `syntax_checker_tool` no código refatorado\n"
            "2. `diff_generator_tool` comparando original e refatorado\n\n"
            f"Código original:\n```python\n{source_code}\n```\n\n"
            f"Código refatorado:\n```python\n{proposal.refactored_code}\n```\n\n"
            "Avalie os 5 critérios das instruções e retorne ReflectionReview. "
            "Defina `final_validated_code=null`."
        )
        response = self._critic.run(prompt)
        return _parse_response(response.content, ReflectionReview)

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
