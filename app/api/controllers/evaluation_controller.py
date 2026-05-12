"""Evaluation controller for evaluation endpoints."""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException

from app.api.dependencies import get_evaluation_service
from app.core.schemas import EvaluationMetrics
from app.services.evaluation_service import EvaluationService


async def evaluate(
    service: Annotated[EvaluationService, Depends(get_evaluation_service)],
) -> EvaluationMetrics:
    try:
        return await service.evaluate()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc