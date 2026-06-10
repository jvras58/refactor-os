"""Evaluation controller for evaluation endpoints."""
from __future__ import annotations

from typing import Annotated

from fastapi import Body, Depends, HTTPException

from app.api.dependencies import get_evaluation_service
from app.core.schemas import (
    CriticEvalRequest,
    CriticMetrics,
    DetectorEvalRequest,
    DetectorMetrics,
    FullEvalRequest,
    FullEvaluationReport,
    RefactorEvalRequest,
    RefactorQualityMetrics,
)
from app.services.evaluation_service import EvaluationService

EvalDep = Annotated[EvaluationService, Depends(get_evaluation_service)]


async def evaluate_detector(
    service: EvalDep,
    body: Annotated[DetectorEvalRequest | None, Body()] = None,
) -> DetectorMetrics:
    """Agente Rastreador — falsos positivos e falsos negativos da detecção.

    Body vazio (ou sem ``samples``) → roda sobre o dataset.
    Body com ``samples`` → roda sobre o código submetido pelo usuário.
    """
    samples = body.samples if body else None
    try:
        return await service.evaluate_detector(samples=samples)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


async def evaluate_refactor(
    service: EvalDep,
    body: Annotated[RefactorEvalRequest | None, Body()] = None,
) -> RefactorQualityMetrics:
    """Agente Refatorador — precisão/qualidade da solução proposta.

    Body vazio (ou sem ``samples``) → roda sobre o dataset.
    Body com ``samples`` → roda sobre o código submetido pelo usuário.
    """
    samples = body.samples if body else None
    try:
        return await service.evaluate_refactor(samples=samples)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


async def evaluate_critic(
    service: EvalDep,
    body: Annotated[CriticEvalRequest | None, Body()] = None,
) -> CriticMetrics:
    """Agente Revisor — confiabilidade do julgamento (false accept / false reject).

    Body vazio (ou sem ``samples``) → roda sobre o dataset.
    Body com ``samples`` → roda sobre o código submetido pelo usuário.
    """
    samples = body.samples if body else None
    try:
        return await service.evaluate_critic(samples=samples)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


async def evaluate_all(
    service: EvalDep,
    body: Annotated[FullEvalRequest | None, Body()] = None,
) -> FullEvaluationReport:
    """Relatório completo dos três agentes.

    Body vazio → todos rodam sobre o dataset.
    Body com ``detector``/``refactor``/``critic`` preenchidos (com ``samples``)
    → cada agente individualmente passa pro modo ad-hoc; os ausentes continuam
    sobre o dataset.
    """
    detector_samples = body.detector.samples if body and body.detector else None
    refactor_samples = body.refactor.samples if body and body.refactor else None
    critic_samples = body.critic.samples if body and body.critic else None
    try:
        return await service.evaluate_all(
            detector_samples=detector_samples,
            refactor_samples=refactor_samples,
            critic_samples=critic_samples,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
