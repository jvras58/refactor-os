"""Type Detector Agent — decides ONE smell/pattern type per call.

Generic by design: the type name/definition is injected into the per-call prompt
(see ``app/core/multi_detector_prompts.py``), not into static instructions. One
agent instance is reused across the 8 individual calls of phase 3 (4 smells +
4 patterns).

Stateless on purpose: each call is an isolated yes/no judgment with no multi-turn
memory and no RAG, unlike the Recommender (which needs Postgres+pgvector for
``search_knowledge_base``). No ``db=`` here — Agno's ``Agent`` defaults it to
``None`` — so this agent runs with only an LLM provider, no Postgres required.
"""
from __future__ import annotations

from agno.agent import Agent

from app.core.llm import build_main_model, build_parser_model
from app.core.multi_detector_prompts import TYPE_DETECTOR_INSTRUCTIONS
from app.core.multi_detector_schemas import TypeDetectionResult


def build_type_detector_agent() -> Agent:
    return Agent(
        name="Type Detector Agent",
        id="multi-detector-type-agent",
        role="Decide se UM tipo específico (smell ou pattern) está presente no código.",
        model=build_main_model(),
        parser_model=build_parser_model(),
        instructions=TYPE_DETECTOR_INSTRUCTIONS,
        output_schema=TypeDetectionResult,
        markdown=False,
    )
