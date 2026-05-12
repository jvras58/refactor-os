"""FastAPI endpoints exposing the refactoring pipeline."""
from __future__ import annotations

from fastapi import APIRouter

from app.api.controllers.agents_controller import detect, refactor
from app.api.controllers.evaluation_controller import evaluate
from app.api.controllers.knowledge_controller import sync_knowledge
from app.core.schemas import EvaluationMetrics, RefactorResult, SmellDetection

router = APIRouter(prefix="/api/v1", tags=["refactor"])

router.add_api_route("/detect", detect, methods=["POST"], response_model=SmellDetection, tags=["agents"])
router.add_api_route("/refactor", refactor, methods=["POST"], response_model=RefactorResult, tags=["agents"])
router.add_api_route("/evaluate", evaluate, methods=["POST"], response_model=EvaluationMetrics, tags=["evaluation"])
router.add_api_route("/knowledge/sync", sync_knowledge, methods=["POST"], tags=["knowledge"])
