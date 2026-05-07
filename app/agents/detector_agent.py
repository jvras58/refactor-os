"""Detector Agent — identifies bad smells using AST and complexity metrics."""
from __future__ import annotations

from agno.agent import Agent
from agno.models.groq import Groq

from app.core.config import get_settings
from app.core.prompts import DETECTOR_INSTRUCTIONS
from app.core.schemas import SmellDetection
from app.db.session import get_db


def build_detector_agent() -> Agent:
    settings = get_settings()
    return Agent(
        name="Detector Agent",
        id="detector-agent",
        role="Detecta bad smells e mede complexidade no código fonte.",
        model=Groq(id=settings.llm_model_id),
        db=get_db(),
        instructions=DETECTOR_INSTRUCTIONS,
        output_schema=SmellDetection,
        markdown=False,
    )
