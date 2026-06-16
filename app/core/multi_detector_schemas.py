"""Pydantic contracts for the new multi-smell/multi-pattern detector pipeline.

Phase 1 (validation) raises ``InvalidPythonCodeError`` and produces no schema.
Phase 2 (heuristic) -> ``HeuristicScan``. Phase 3 (paired LLM checks) ->
``PairedDetectionResponse`` per call, aggregated into ``DetectionScanResult``.
Phase 4 (compilation) is implemented by ``ResultCompiler`` strategies in
``app/services/multi_detector_service.py`` and is not a fixed schema by design.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from app.core.multi_detector_types import SmellType


class SmellHeuristicSignal(BaseModel):
    """Deterministic AST-only signal for a single smell — always present per smell,
    even when the heuristic found nothing (``possible=False, score=0.0``)."""

    smell_type: SmellType
    possible: bool
    score: float = Field(ge=0.0, le=1.0)
    evidence: list[str] = Field(default_factory=list)
    line_start: int | None = None
    line_end: int | None = None


class HeuristicScan(BaseModel):
    """One ``SmellHeuristicSignal`` per in-scope smell (phase 2 output)."""

    signals: dict[SmellType, SmellHeuristicSignal]


class TypeEvidence(BaseModel):
    """A single location backing a smell/pattern detection."""

    local: str = Field(description="Nome da classe/método (ex.: 'Pedido.criar') ou '<módulo>'.")
    linhas: list[int] = Field(description="[linha_inicial, linha_final] do trecho evidenciado.")


class TypeDetectionResult(BaseModel):
    """LLM verdict for ONE smell or pattern type (phase 3, one half of a paired call)."""

    type_name: str = Field(description="Nome exato do smell ou pattern avaliado nesta chamada.")
    detected: bool
    evidencias: list[TypeEvidence] = Field(default_factory=list)
    reasoning: str = Field(description="Justificativa técnica da decisão.")


class PairedDetectionResponse(BaseModel):
    """Output schema of a single phase-3 LLM call — always exactly 2 independent verdicts."""

    result_a: TypeDetectionResult
    result_b: TypeDetectionResult


class DetectionScanResult(BaseModel):
    """Raw output of phases 1-3 — everything checked, both detected and not.

    Phase 4 compilers consume this to produce whatever shape a downstream
    consumer needs (see ``ResultCompiler`` in the service module).
    """

    heuristic_scan: HeuristicScan
    type_results: list[TypeDetectionResult]
