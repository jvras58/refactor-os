"""MultiDetectorService — the multi-smell/multi-pattern detector of the pipeline.

Four explicit phases:
1. Validation — fails fast if ``source_code`` doesn't compile as Python.
2. Heuristic scan (no LLM) — scores all 4 in-scope smells, always (even absent ones).
3. LLM verification, one type per call — 8 calls (4 smells + 4 patterns), each
   deciding a single independent type. Heuristic signals inform every prompt but
   never gate/skip a check.
4. Compilation — a swappable strategy (``ResultCompiler``) shapes the raw scan for
   whichever consumer needs it (ground-truth comparison, Recommender input, etc.).
"""
from __future__ import annotations

import ast
import logging
from typing import Protocol

from agno.agent import Agent

from app.agents.detector_agent import build_type_detector_agent
from app.core.exceptions import InvalidPythonCodeError
from app.core.prompts import PATTERN_DEFINITIONS, SMELL_DEFINITIONS, build_type_prompt
from app.core.schemas import (
    PATTERN_TO_SMELL,
    DetectionScanResult,
    HeuristicScan,
    PatternType,
    SmellHeuristicSignal,
    SmellType,
    TypeDetectionResult,
)
from app.tools.heuristic_engine import score_all_smells
from app.utils.retry import arun_typed

logger = logging.getLogger(__name__)


class ResultCompiler(Protocol):
    """Phase 4 contract — deliberately swappable per consumer."""

    def compile(self, scan: DetectionScanResult) -> object: ...


class GroundTruthArrayCompiler:
    """Compiles to ``list[str]`` of detected type names — matches the ``problems``
    field of ``dataset/ground_truth_detector.json``."""

    def compile(self, scan: DetectionScanResult) -> list[str]:
        return scan.detected_names()


class MultiDetectorService:
    """Plain service class — no FastAPI/Request dependency. Entry point: ``detect()``."""

    def __init__(self, compiler: ResultCompiler | None = None) -> None:
        self._compiler = compiler or GroundTruthArrayCompiler()
        self._agent: Agent = build_type_detector_agent()

    # ------------------------------------------------------------- phase 1
    @staticmethod
    def _validate_python(source_code: str) -> None:
        logger.info("[fase 1] entrada: %d chars de código-fonte", len(source_code))
        logger.debug("[fase 1] entrada (código completo):\n%s", source_code)
        try:
            ast.parse(source_code)
        except SyntaxError as exc:
            logger.warning("[fase 1] saída: inválido — %s (linha %s)", exc.msg, exc.lineno)
            raise InvalidPythonCodeError(
                f"código não compila como Python: {exc.msg}", line=exc.lineno
            ) from exc
        logger.info("[fase 1] saída: código Python válido")

    # ------------------------------------------------------------- phase 2
    @staticmethod
    def _run_heuristics(source_code: str) -> HeuristicScan:
        logger.info("[fase 2] entrada: %d chars de código-fonte", len(source_code))
        raw = score_all_smells(source_code)
        signals: dict[SmellType, SmellHeuristicSignal] = {}
        for smell_type, signal in raw.items():
            if signal is None:
                signals[smell_type] = SmellHeuristicSignal(
                    smell_type=smell_type, possible=False, score=0.0
                )
            else:
                signals[smell_type] = SmellHeuristicSignal(
                    smell_type=smell_type,
                    possible=True,
                    score=signal.score,
                    evidence=signal.evidence,
                    line_start=signal.line_start,
                    line_end=signal.line_end,
                )
        for smell_type, sig in signals.items():
            logger.info(
                "[fase 2] saída: %s -> possible=%s score=%.2f evidence=%s",
                smell_type.value, sig.possible, sig.score, sig.evidence,
            )
        return HeuristicScan(signals=signals)

    # ------------------------------------------------------------- phase 3
    @staticmethod
    def _smell_heuristic_text(scan: HeuristicScan, smell: SmellType) -> str:
        signal = scan.signals[smell]
        if not signal.possible:
            return f"- {smell.value}: heurística não encontrou evidência (score 0.0)."
        evidence = " ".join(signal.evidence) or "sem detalhe adicional."
        location = (
            f"linhas {signal.line_start}-{signal.line_end}"
            if signal.line_start is not None
            else "linha n/d"
        )
        return f"- {smell.value}: score {signal.score:.2f} ({location}) — {evidence}"

    async def _check_type(
        self,
        source_code: str,
        type_name: str,
        type_definition: str,
        heuristic_context: str,
    ) -> TypeDetectionResult:
        prompt = build_type_prompt(
            type_name=type_name,
            type_definition=type_definition,
            heuristic_context=heuristic_context,
            source_code=source_code,
        )
        label = f"MultiDetector[{type_name}]"
        logger.info("[fase 3] entrada: tipo %s — prompt com %d chars", type_name, len(prompt))
        logger.debug("[fase 3] entrada (prompt completo, %s):\n%s", label, prompt)
        result = await arun_typed(
            self._agent.arun,
            prompt,
            schema=TypeDetectionResult,
            label=label,
        )
        logger.info("[fase 3] saída (%s): detected=%s", label, result.detected)
        logger.debug("[fase 3] saída completa (%s): %s", label, result.model_dump_json())
        return result

    async def _check_smell(
        self, source_code: str, scan: HeuristicScan, smell: SmellType
    ) -> TypeDetectionResult:
        context = self._smell_heuristic_text(scan, smell)
        return await self._check_type(source_code, smell.value, SMELL_DEFINITIONS[smell], context)

    async def _check_pattern(
        self, source_code: str, scan: HeuristicScan, pattern: PatternType
    ) -> TypeDetectionResult:
        related_smell = PATTERN_TO_SMELL[pattern]
        base = self._smell_heuristic_text(scan, related_smell)
        context = (
            f"{base} (smell relacionado a {pattern.value} — a presença do pattern "
            "NÃO depende deste smell estar presente)"
        )
        return await self._check_type(source_code, pattern.value, PATTERN_DEFINITIONS[pattern], context)

    # ------------------------------------------------------------- orchestration
    async def detect(self, source_code: str) -> DetectionScanResult:
        """Runs phases 1-3. Phase 4 (compile) is a separate, explicit call."""
        self._validate_python(source_code)
        heuristic_scan = self._run_heuristics(source_code)

        # Phase 3 — 8 calls total, one per type, in enum order (4 smells + 4 patterns).
        type_results: list[TypeDetectionResult] = []
        for smell in SmellType:
            type_results.append(await self._check_smell(source_code, heuristic_scan, smell))
        for pattern in PatternType:
            type_results.append(await self._check_pattern(source_code, heuristic_scan, pattern))

        return DetectionScanResult(heuristic_scan=heuristic_scan, type_results=type_results)

    # ------------------------------------------------------------- phase 4
    def compile(self, scan: DetectionScanResult) -> object:
        logger.info(
            "[fase 4] entrada: %d resultados de tipo via %s",
            len(scan.type_results), type(self._compiler).__name__,
        )
        result = self._compiler.compile(scan)
        logger.info("[fase 4] saída: %s", result)
        return result
