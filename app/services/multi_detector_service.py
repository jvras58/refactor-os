"""MultiDetectorService — the new, from-scratch multi-smell/multi-pattern detector.

Four explicit phases:
1. Validation — fails fast if ``source_code`` doesn't compile as Python.
2. Heuristic scan (no LLM) — scores all 4 in-scope smells, always (even absent ones).
3. Paired LLM verification — 4 calls (2 smell pairs + 2 pattern pairs) instead of 8,
   each deciding 2 independent types in one shot. Heuristic signals inform every
   prompt but never gate/skip a check.
4. Compilation — a swappable strategy (``ResultCompiler``) shapes the raw scan for
   whichever consumer needs it (ground-truth comparison, Recommender input, etc.).

Does not import or modify anything from the existing ``RefactorService``/
``detector_agent.py``/``DETECTOR_INSTRUCTIONS`` — fully independent pipeline.
"""
from __future__ import annotations

import ast
import logging
from typing import Protocol

from agno.agent import Agent

from app.agents.multi_detector_agent import build_pair_detector_agent
from app.core.multi_detector_exceptions import InvalidPythonCodeError
from app.core.multi_detector_prompts import (
    PATTERN_DEFINITIONS,
    SMELL_DEFINITIONS,
    build_pair_prompt,
)
from app.core.multi_detector_schemas import (
    DetectionScanResult,
    HeuristicScan,
    PairedDetectionResponse,
    SmellHeuristicSignal,
    TypeDetectionResult,
)
from app.core.multi_detector_types import PATTERN_TO_SMELL, PatternType, SmellType
from app.core.schemas import BadSmellType
from app.tools.heuristic_engine import score_all_smells
from app.utils.retry import arun_typed

logger = logging.getLogger(__name__)

# Phase 3 grouping — 4 calls instead of 8. Change these tuples to regroup later.
_SMELL_PAIRS: tuple[tuple[SmellType, SmellType], ...] = (
    (SmellType.COMPLEX_SWITCH, SmellType.LONG_PARAMETER),
    (SmellType.GOD_CLASS, SmellType.DUPLICATED_CODE),
)
_PATTERN_PAIRS: tuple[tuple[PatternType, PatternType], ...] = (
    (PatternType.STRATEGY, PatternType.BUILDER),
    (PatternType.FACADE, PatternType.TEMPLATE_METHOD),
)

# multi_detector_types.SmellType values match BadSmellType values 1:1 (minus Tight
# Coupling) — this lets phase 2 reuse heuristic_engine's scorers without duplicating them.
_SMELL_TYPE_TO_BAD_SMELL: dict[SmellType, BadSmellType] = {
    SmellType.COMPLEX_SWITCH: BadSmellType.COMPLEX_SWITCH,
    SmellType.LONG_PARAMETER: BadSmellType.LONG_PARAMETER,
    SmellType.GOD_CLASS: BadSmellType.GOD_CLASS,
    SmellType.DUPLICATED_CODE: BadSmellType.DUPLICATED_CODE,
}


class ResultCompiler(Protocol):
    """Phase 4 contract — deliberately swappable per consumer."""

    def compile(self, scan: DetectionScanResult) -> object: ...


class GroundTruthArrayCompiler:
    """Compiles to ``list[str]`` of detected type names — matches the ``problems``
    field of ``dataset_2/ground_truth_detector.json``."""

    def compile(self, scan: DetectionScanResult) -> list[str]:
        return [result.type_name for result in scan.type_results if result.detected]


class MultiDetectorService:
    """Plain service class — no FastAPI/Request dependency. Entry point: ``detect()``."""

    def __init__(self, compiler: ResultCompiler | None = None) -> None:
        self._compiler = compiler or GroundTruthArrayCompiler()
        self._agent: Agent = build_pair_detector_agent()

    # ------------------------------------------------------------- phase 1
    @staticmethod
    def _validate_python(source_code: str) -> None:
        try:
            ast.parse(source_code)
        except SyntaxError as exc:
            raise InvalidPythonCodeError(
                f"código não compila como Python: {exc.msg}", line=exc.lineno
            ) from exc

    # ------------------------------------------------------------- phase 2
    @staticmethod
    def _run_heuristics(source_code: str) -> HeuristicScan:
        raw = score_all_smells(source_code)
        signals: dict[SmellType, SmellHeuristicSignal] = {}
        for smell_type, bad_smell in _SMELL_TYPE_TO_BAD_SMELL.items():
            signal = raw.get(bad_smell)
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

    async def _check_pair(
        self,
        source_code: str,
        type_a_name: str,
        type_a_definition: str,
        type_b_name: str,
        type_b_definition: str,
        heuristic_context: str,
    ) -> list[TypeDetectionResult]:
        prompt = build_pair_prompt(
            type_a_name=type_a_name,
            type_a_definition=type_a_definition,
            type_b_name=type_b_name,
            type_b_definition=type_b_definition,
            heuristic_context=heuristic_context,
            source_code=source_code,
        )
        response = await arun_typed(
            self._agent.arun,
            prompt,
            schema=PairedDetectionResponse,
            label=f"MultiDetector[{type_a_name} + {type_b_name}]",
        )
        return [response.result_a, response.result_b]

    async def _check_smell_pair(
        self, source_code: str, scan: HeuristicScan, pair: tuple[SmellType, SmellType]
    ) -> list[TypeDetectionResult]:
        type_a, type_b = pair
        context = "\n".join(self._smell_heuristic_text(scan, smell) for smell in pair)
        return await self._check_pair(
            source_code,
            type_a.value, SMELL_DEFINITIONS[type_a],
            type_b.value, SMELL_DEFINITIONS[type_b],
            context,
        )

    async def _check_pattern_pair(
        self, source_code: str, scan: HeuristicScan, pair: tuple[PatternType, PatternType]
    ) -> list[TypeDetectionResult]:
        type_a, type_b = pair
        lines = []
        for pattern in pair:
            related_smell = PATTERN_TO_SMELL[pattern]
            base = self._smell_heuristic_text(scan, related_smell)
            lines.append(
                f"{base} (smell relacionado a {pattern.value} — a presença do pattern "
                "NÃO depende deste smell estar presente)"
            )
        context = "\n".join(lines)
        return await self._check_pair(
            source_code,
            type_a.value, PATTERN_DEFINITIONS[type_a],
            type_b.value, PATTERN_DEFINITIONS[type_b],
            context,
        )

    # ------------------------------------------------------------- orchestration
    async def detect(self, source_code: str) -> DetectionScanResult:
        """Runs phases 1-3. Phase 4 (compile) is a separate, explicit call."""
        self._validate_python(source_code)
        heuristic_scan = self._run_heuristics(source_code)

        type_results: list[TypeDetectionResult] = []
        for smell_pair in _SMELL_PAIRS:
            type_results += await self._check_smell_pair(source_code, heuristic_scan, smell_pair)
        for pattern_pair in _PATTERN_PAIRS:
            type_results += await self._check_pattern_pair(source_code, heuristic_scan, pattern_pair)

        return DetectionScanResult(heuristic_scan=heuristic_scan, type_results=type_results)

    # ------------------------------------------------------------- phase 4
    def compile(self, scan: DetectionScanResult) -> object:
        return self._compiler.compile(scan)
