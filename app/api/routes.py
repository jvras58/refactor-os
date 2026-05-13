"""FastAPI endpoints exposing the refactoring pipeline."""
from __future__ import annotations

from fastapi import APIRouter

from app.api.controllers.agents_controller import detect, refactor
from app.api.controllers.dashboard_controller import render_dashboard
from app.api.controllers.evaluation_controller import evaluate
from app.api.controllers.knowledge_controller import sync_knowledge
from app.core.schemas import EvaluationMetrics, RefactorResult, SmellDetection

routerAPI = APIRouter(prefix="/api/v1", tags=["refactor"])


routerAPI.add_api_route("/detect", detect, methods=["POST"], response_model=SmellDetection, tags=["agents"])
routerAPI.add_api_route("/refactor", refactor, methods=["POST"], response_model=RefactorResult, tags=["agents"])
routerAPI.add_api_route("/evaluate", evaluate, methods=["POST"], response_model=EvaluationMetrics, tags=["evaluation"])
routerAPI.add_api_route("/knowledge/sync", sync_knowledge, methods=["POST"], tags=["knowledge"])


routerDash = APIRouter(prefix="", tags=["dashboard"])

routerDash.add_api_route("/dashboard", render_dashboard, methods=["GET"], include_in_schema=False)
