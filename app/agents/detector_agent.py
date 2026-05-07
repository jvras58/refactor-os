"""Detector Agent — identifies bad smells using AST and complexity metrics."""
from __future__ import annotations

from agno.agent import Agent
from agno.models.groq import Groq

from app.core.config import get_settings
from app.core.prompts import DETECTOR_INSTRUCTIONS
from app.db.session import get_db
from app.tools.ast_tools import ast_analyzer_tool, read_source_code_tool


def build_detector_agent() -> Agent:
    settings = get_settings()
    groq = Groq(api_key=settings.groq_api_key, id=settings.llm_model_id)
    return Agent(
        name="Detector Agent",
        id="detector-agent",
        role="Detecta bad smells e mede complexidade no código fonte.",
        model=groq,
        db=get_db(),
        tools=[read_source_code_tool, ast_analyzer_tool],
        instructions=DETECTOR_INSTRUCTIONS,
        markdown=False,
    )
