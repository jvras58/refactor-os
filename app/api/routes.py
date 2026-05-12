"""FastAPI endpoints exposing the refactoring pipeline."""
from __future__ import annotations

from fastapi import APIRouter

from app.api.controllers.agents_controller import detect, refactor
from app.api.controllers.evaluation_controller import evaluate
from app.api.controllers.knowledge_controller import sync_knowledge
from app.core.schemas import EvaluationMetrics, RefactorResult, SmellDetection

router = APIRouter(prefix="/api/v1", tags=["refactor"])

router.post("/detect", detect, response_model=SmellDetection, tags=["agents"])
router.post("/refactor", refactor, response_model=RefactorResult, tags=["agents"])
router.post("/evaluate", evaluate, response_model=EvaluationMetrics, tags=["evaluation"])
router.post("/knowledge/sync", sync_knowledge, tags=["knowledge"])
