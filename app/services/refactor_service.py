"""Orchestrates the deterministic Detector → Recommender → Critic pipeline.

Detection is the multi-detector (``MultiDetectorService``): a multi-label scan
that decides all 4 smells + 4 patterns independently. ``run`` then picks ONE
target from the scan (the detected smell with the strongest heuristic score,
falling back to a detected pattern) and drives the explicit reflection loop
(up to N iterations) outside the Team abstraction so the academic evaluation
can measure each stage independently.

Each agent is built with a ``parser_model`` (see ``app/core/llm.py``) so the
main Mistral call handles tool/skill calling without forced json_mode, while a
second Mistral call extracts the Pydantic structured output. ``arun_typed``
wraps that with two extra layers of defense: rate-limit backoff on 429s and a
retry when the parser still returns raw text.
"""
from __future__ import annotations

import logging

from app.agents.critic_agent import build_critic_agent
from app.agents.recommender_agent import build_recommender_agent
from app.core.config import get_settings
from app.core.exceptions import InvalidPythonCodeError
from app.core.schemas import (
    PATTERN_TO_SMELL,
    SMELL_TO_PATTERN,
    DetectionScanResult,
    PatternType,
    RefactoringProposal,
    RefactorRequest,
    RefactorResult,
    ReflectionReview,
    SmellType,
    TypeDetectionResult,
)
from app.services.code_repair import repair_refactored_code
from app.services.multi_detector_service import MultiDetectorService
from app.tools.logic_signals import analyze_logic_preservation, format_logic_prior
from app.utils.retry import arun_typed

logger = logging.getLogger(__name__)

_PATTERN_TO_SKILL: dict[PatternType, str] = {
    PatternType.STRATEGY: "strategy-pattern",
    PatternType.BUILDER: "builder-parameter-object",
    PatternType.FACADE: "facade-srp",
    PatternType.TEMPLATE_METHOD: "template-method",
}


class RefactorService:
    """High-level façade that runs the multi-agent refactoring pipeline."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._detector = MultiDetectorService()
        self._recommender = build_recommender_agent()
        self._critic = build_critic_agent()

    async def detect(self, source_code: str) -> DetectionScanResult:
        """Multi-label scan: 4 smells + 4 patterns decided independently.

        Raises ``InvalidPythonCodeError`` when the input does not parse.
        """
        return await self._detector.detect(source_code)

    @staticmethod
    def _select_target(
        scan: DetectionScanResult,
    ) -> tuple[SmellType | None, PatternType | None, TypeDetectionResult | None]:
        """Picks ONE (smell, pattern) target for the Recommender from the scan.

        Preference: the detected smell with the strongest heuristic score (its
        pattern comes from the canonical mapping). If no smell was detected but
        a pattern is applicable, targets that pattern directly.
        """
        detected = {result.type_name: result for result in scan.type_results if result.detected}

        smells = [smell for smell in SmellType if smell.value in detected]
        if smells:
            smell = max(smells, key=lambda s: scan.heuristic_scan.signals[s].score)
            return smell, SMELL_TO_PATTERN[smell], detected[smell.value]

        patterns = [pattern for pattern in PatternType if pattern.value in detected]
        if patterns:
            pattern = patterns[0]
            return PATTERN_TO_SMELL[pattern], pattern, detected[pattern.value]

        return None, None, None

    @staticmethod
    def _format_evidence(detection: TypeDetectionResult) -> str:
        if not detection.evidencias:
            return "n/d"
        return "; ".join(
            f"{ev.local} (linhas {'-'.join(str(line_num) for line_num in ev.linhas)})"
            for ev in detection.evidencias
        )

    async def propose(
        self,
        source_code: str,
        target_smell: SmellType,
        target_pattern: PatternType,
        detection: TypeDetectionResult,
        prior_critique: str | None = None,
    ) -> RefactoringProposal:
        skill_name = _PATTERN_TO_SKILL[target_pattern]
        critique_block = (
            f"\n\nFeedback do Critic na rodada anterior (corrija obrigatoriamente):\n{prior_critique}"
            if prior_critique
            else ""
        )
        prompt = (
            f"Smell detectado: {target_smell.value}\n"
            f"Pattern obrigatório: {target_pattern.value}\n"
            f"Skill obrigatório: {skill_name}\n"
            f"Justificativa do Detector: {detection.reasoning}\n"
            f"Evidências: {self._format_evidence(detection)}\n\n"
            f"Use obrigatoriamente `get_skill_instructions(name='{skill_name}')` para consultar "
            "a estrutura canônica, regras estritas e o exemplo canônico do pattern antes de "
            "propor o código.\n\n"
            f"Código original:\n```python\n{source_code}\n```"
            f"{critique_block}\n\n"
            "Retorne RefactoringProposal. "
            "No campo `refactored_code` use apenas aspas simples ou duplas — nunca aspas triplas."
        )
        proposal = await arun_typed(
            self._recommender.arun, prompt, schema=RefactoringProposal, label="Recommender"
        )
        # Sanitiza artefato de indentação (def/class após decorador) antes do Critic/avaliação.
        proposal.refactored_code = repair_refactored_code(proposal.refactored_code)
        return proposal

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
            f"{logic_prior}\n\n"
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
            scan = await self.detect(request.source_code)
        except InvalidPythonCodeError as exc:
            logger.warning("Detector rejected invalid Python input: %s", exc)
            return RefactorResult(
                approved=False,
                iterations=0,
                error=f"Código de entrada não compila como Python: {exc}",
            )
        except Exception:
            logger.exception("Detector stage failed")
            return RefactorResult(
                approved=False,
                iterations=0,
                error="Detector falhou — verifique logs para detalhes.",
            )

        detected_problems = scan.detected_names()
        target_smell, target_pattern, target_detection = self._select_target(scan)

        if target_smell is None or target_pattern is None or target_detection is None:
            return RefactorResult(
                detection=scan,
                detected_problems=detected_problems,
                approved=False,
                iterations=0,
            )

        proposal: RefactoringProposal | None = None
        review: ReflectionReview | None = None
        critique: str | None = None

        for iteration in range(1, self._settings.max_reflection_iterations + 1):
            logger.info("Reflection iteration %s", iteration)
            try:
                proposal = await self.propose(
                    request.source_code,
                    target_smell,
                    target_pattern,
                    target_detection,
                    prior_critique=critique,
                )
            except Exception:
                logger.exception("Recommender stage failed at iteration %s", iteration)
                return RefactorResult(
                    detection=scan,
                    detected_problems=detected_problems,
                    target_smell=target_smell,
                    target_pattern=target_pattern,
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
                    detection=scan,
                    detected_problems=detected_problems,
                    target_smell=target_smell,
                    target_pattern=target_pattern,
                    proposal=proposal,
                    review=review,
                    iterations=iteration,
                    approved=False,
                    error=f"Critic falhou na iteração {iteration} — verifique logs.",
                )

            if review.is_approved:
                return RefactorResult(
                    detection=scan,
                    detected_problems=detected_problems,
                    target_smell=target_smell,
                    target_pattern=target_pattern,
                    proposal=proposal,
                    review=review,
                    iterations=iteration,
                    approved=True,
                )
            critique = review.critique

        return RefactorResult(
            detection=scan,
            detected_problems=detected_problems,
            target_smell=target_smell,
            target_pattern=target_pattern,
            proposal=proposal,
            review=review,
            iterations=self._settings.max_reflection_iterations,
            approved=False,
        )
