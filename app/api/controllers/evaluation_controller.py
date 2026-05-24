"""Evaluation controller for evaluation endpoints."""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException

from app.api.dependencies import get_evaluation_service
from app.core.schemas import (
    CriticMetrics,
    DetectorMetrics,
    EvaluationMetrics,
    FullEvaluationReport,
    RefactorQualityMetrics,
)
from app.services.evaluation_service import EvaluationService

EvalDep = Annotated[EvaluationService, Depends(get_evaluation_service)]


async def evaluate(service: EvalDep) -> EvaluationMetrics:
    try:
        return await service.evaluate()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


async def evaluate_detector(service: EvalDep) -> DetectorMetrics:
    """Agente Rastreador — falsos positivos e falsos negativos da detecção."""
    try:
        return await service.evaluate_detector()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


async def evaluate_refactor(service: EvalDep) -> RefactorQualityMetrics:
    """Agente Refatorador — precisão/qualidade da solução proposta."""
    try:
        return await service.evaluate_refactor()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


async def evaluate_critic(service: EvalDep) -> CriticMetrics:
    """Agente Revisor — confiabilidade do julgamento (false accept / false reject)."""
    try:
        return await service.evaluate_critic()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


async def evaluate_all(service: EvalDep) -> FullEvaluationReport:
    """Relatório completo dos três agentes."""
    try:
        return await service.evaluate_all()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
