"""Detector Agent — identifies bad smells using AST and complexity metrics."""
from __future__ import annotations

from agno.agent import Agent

from app.core.llm import build_main_model, build_parser_model
from app.core.prompts import DETECTOR_INSTRUCTIONS
from app.core.schemas import SmellDetection
from app.db.session import get_db
from app.tools.ast_tools import ast_analyzer_tool


def build_detector_agent() -> Agent:
    return Agent(
        name="Detector Agent",
        id="detector-agent",
        role="Detecta bad smells e mede complexidade no código fonte.",
        model=build_main_model(),
        parser_model=build_parser_model(),
        db=get_db(),
        # TODO: remover ast_analyzer_tool. Com a matriz heurística (app/tools/heuristic_engine.py)
        # injetada no prompt por RefactorService.detect(), este tool reparseia o mesmo AST que o
        # prior já analisou — ficou redundante. Antes de remover, ajustar DETECTOR_INSTRUCTIONS
        # (hoje exige "SEMPRE chame ast_analyzer_tool"). Ver docs/agentic_patterns.md §17.
        tools=[ast_analyzer_tool],
        instructions=DETECTOR_INSTRUCTIONS,
        output_schema=SmellDetection,
        markdown=False,
    )
