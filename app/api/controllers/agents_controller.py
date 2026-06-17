"""Agents controller for detection and refactoring endpoints."""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException

from app.api.dependencies import get_refactor_service
from app.core.exceptions import InvalidPythonCodeError
from app.core.schemas import DetectionScanResult, RefactorRequest, RefactorResult
from app.services.refactor_service import RefactorService


async def detect(
    request: RefactorRequest,
    service: Annotated[RefactorService, Depends(get_refactor_service)],
) -> DetectionScanResult:
    try:
        return await service.detect(request.source_code)
    except InvalidPythonCodeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


async def refactor(
    request: RefactorRequest,
    service: Annotated[RefactorService, Depends(get_refactor_service)],
) -> RefactorResult:
    return await service.run(request)