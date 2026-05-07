"""FastAPI endpoints exposing the refactoring pipeline."""
from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.core.schemas import (
    EvaluationMetrics,
    RefactorRequest,
    RefactorResult,
    SmellDetection,
)
from app.services.evaluation_service import EvaluationService
from app.services.knowledge_service import load_patterns_into_kb
from app.services.refactor_service import RefactorService

router = APIRouter(prefix="/api/v1", tags=["refactor"])


@lru_cache
def _refactor_service() -> RefactorService:
    return RefactorService()


@lru_cache
def _evaluation_service() -> EvaluationService:
    return EvaluationService(_refactor_service())


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/detect", response_model=SmellDetection)
def detect(
    request: RefactorRequest,
    service: Annotated[RefactorService, Depends(_refactor_service)],
) -> SmellDetection:
    return service.detect(request.source_code)


@router.post("/refactor", response_model=RefactorResult)
def refactor(
    request: RefactorRequest,
    service: Annotated[RefactorService, Depends(_refactor_service)],
) -> RefactorResult:
    return service.run(request)


@router.post("/evaluate", response_model=EvaluationMetrics)
def evaluate(
    service: Annotated[EvaluationService, Depends(_evaluation_service)],
) -> EvaluationMetrics:
    try:
        return service.evaluate()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/knowledge/sync")
def sync_knowledge() -> dict[str, int]:
    loaded = load_patterns_into_kb()
    return {"loaded": loaded}
