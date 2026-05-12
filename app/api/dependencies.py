"""API dependencies."""
from __future__ import annotations

from functools import lru_cache

from app.services.evaluation_service import EvaluationService
from app.services.refactor_service import RefactorService


@lru_cache
def get_refactor_service() -> RefactorService:
    return RefactorService()


@lru_cache
def get_evaluation_service() -> EvaluationService:
    return EvaluationService(get_refactor_service())