"""Agents controller for detection and refactoring endpoints."""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.api.dependencies import get_refactor_service
from app.core.schemas import RefactorRequest, RefactorResult, SmellDetection
from app.services.refactor_service import RefactorService


def detect(
    request: RefactorRequest,
    service: Annotated[RefactorService, Depends(get_refactor_service)],
) -> SmellDetection:
    return service.detect(request.source_code)


def refactor(
    request: RefactorRequest,
    service: Annotated[RefactorService, Depends(get_refactor_service)],
) -> RefactorResult:
    return service.run(request)