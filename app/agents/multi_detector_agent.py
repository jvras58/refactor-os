"""Pair Detector Agent — decides 2 independent smell/pattern types per call.

Generic by design: the 2 type names/definitions are injected into the per-call
prompt (see ``app/core/multi_detector_prompts.py``), not into static instructions.
One agent instance is reused across the 4 paired calls of phase 3.

Stateless on purpose: each call is an isolated yes/no judgment with no multi-turn
memory and no RAG, unlike the Recommender (which needs Postgres+pgvector for
``search_knowledge_base``). No ``db=`` here — Agno's ``Agent`` defaults it to
``None`` — so this agent runs with only an LLM provider, no Postgres required.
"""
from __future__ import annotations

from agno.agent import Agent

from app.core.llm import build_main_model, build_parser_model
from app.core.multi_detector_prompts import PAIR_DETECTOR_INSTRUCTIONS
from app.core.multi_detector_schemas import PairedDetectionResponse


def build_pair_detector_agent() -> Agent:
    return Agent(
        name="Pair Detector Agent",
        id="multi-detector-pair-agent",
        role="Decide se cada um de 2 tipos independentes (smell ou pattern) está presente no código.",
        model=build_main_model(),
        parser_model=build_parser_model(),
        instructions=PAIR_DETECTOR_INSTRUCTIONS,
        output_schema=PairedDetectionResponse,
        markdown=False,
    )
