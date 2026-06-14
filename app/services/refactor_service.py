"""Orchestrates the deterministic Detector → Recommender → Critic pipeline.

Drives the explicit reflection loop (up to N iterations) outside the Team
abstraction so the academic evaluation can measure each stage independently.

Each agent is built with a ``parser_model`` (see ``app/core/llm.py``) so the
main Mistral call handles tool/skill calling without forced json_mode, while a
second Mistral call extracts the Pydantic structured output. ``arun_typed``
wraps that with two extra layers of defense: rate-limit backoff on 429s and a
retry when the parser still returns raw text.
"""
from __future__ import annotations

import logging

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
from app.tools.heuristic_engine import format_prior, score_smells
from app.tools.logic_signals import analyze_logic_preservation, format_logic_prior
from app.utils.retry import arun_typed

logger = logging.getLogger(__name__)

_DETECT_FALLBACK = SmellDetection(
    has_smell=False,
    smell_type=BadSmellType.NO_SMELL,
    reasoning="Detector falhou — erro interno ao chamar o agente.",
)

_PATTERN_TO_SKILL: dict[DesignPatternType, str] = {
    DesignPatternType.STRATEGY: "strategy-pattern",
    DesignPatternType.BUILDER: "builder-parameter-object",
    DesignPatternType.FACADE_SRP: "facade-srp",
    DesignPatternType.DEPENDENCY_INJECTION: "dependency-injection",
    DesignPatternType.TEMPLATE_METHOD: "template-method",
}


class RefactorService:
    """High-level façade that runs the multi-agent refactoring pipeline."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._detector = build_detector_agent()
        self._recommender = build_recommender_agent()
        self._critic = build_critic_agent()

    async def detect(self, source_code: str) -> SmellDetection:
        prior = format_prior(score_smells(source_code))
        prompt = (
            "Analise o seguinte código-fonte e retorne um SmellDetection.\n"
            "Use obrigatoriamente `ast_analyzer_tool` antes de concluir.\n\n"
            f"--- Prior da matriz heurística ---\n{prior}\n--- fim do prior ---\n\n"
            f"```python\n{source_code}\n```"
        )
        return await arun_typed(
            self._detector.arun, prompt, schema=SmellDetection, label="Detector"
        )

    async def propose(
        self,
        source_code: str,
        detection: SmellDetection,
        prior_critique: str | None = None,
    ) -> RefactoringProposal:
        expected = SMELL_TO_PATTERN.get(detection.smell_type, DesignPatternType.NONE)
        skill_name = _PATTERN_TO_SKILL.get(expected, "")
        critique_block = (
            f"\n\nFeedback do Critic na rodada anterior (corrija obrigatoriamente):\n{prior_critique}"
            if prior_critique
            else ""
        )
        prompt = (
            f"Smell detectado: {detection.smell_type.value}\n"
            f"Pattern obrigatório: {expected.value}\n"
            f"Skill obrigatório: {skill_name}\n"
            f"Justificativa do Detector: {detection.reasoning}\n"
            f"Linhas afetadas: {detection.line_start}-{detection.line_end}\n\n"
            f"Use obrigatoriamente `get_skill_instructions(name='{skill_name}')` para consultar "
            "a estrutura canônica, regras estritas e o exemplo canônico do pattern antes de "
            "propor o código.\n\n"
            f"Código original:\n```python\n{source_code}\n```"
            f"{critique_block}\n\n"
            "Retorne RefactoringProposal. "
            "No campo `refactored_code` use apenas aspas simples ou duplas — nunca aspas triplas."
        )
        return await arun_typed(
            self._recommender.arun, prompt, schema=RefactoringProposal, label="Recommender"
        )

    async def review(
        self,
        source_code: str,
        proposal: RefactoringProposal,
    ) -> ReflectionReview:
        logic_prior = format_logic_prior(
            analyze_logic_preservation(source_code, proposal.refactored_code)
        )
        prompt = (
            f"Pattern aplicado: {proposal.applied_pattern.value}\n\n"
            "Use obrigatoriamente:\n"
            "1. `syntax_checker_tool` no código refatorado\n"
            "2. `diff_generator_tool` comparando original e refatorado\n\n"
            f"--- {logic_prior} ---\n\n"
            f"Código original:\n```python\n{source_code}\n```\n\n"
            f"Código refatorado:\n```python\n{proposal.refactored_code}\n```\n\n"
            "Avalie os 5 critérios das instruções e retorne ReflectionReview. "
            "Defina `final_validated_code=null`."
        )
        return await arun_typed(
            self._critic.arun, prompt, schema=ReflectionReview, label="Critic"
        )

    async def run(self, request: RefactorRequest) -> RefactorResult:
        try:
            detection = await self.detect(request.source_code)
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
                proposal = await self.propose(request.source_code, detection, prior_critique=critique)
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
                review = await self.review(request.source_code, proposal)
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
