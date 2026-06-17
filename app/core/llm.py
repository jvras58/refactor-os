"""Mistral model builders shared by all agents.

We expose a **main model** (used for tool/skill calling) and a **parser model**
(used by Agno to extract the structured output from the main model's response).

The split exists because Mistral's JSON-mode is incompatible with tool/skill
calls in the same request — forcing both leads to empty responses. Agno's
``parser_model`` parameter delegates the JSON extraction to a second call where
no tools are exposed, which is the supported workaround.
"""
from __future__ import annotations

from agno.models.mistral import MistralChat

from app.core.config import get_settings


def build_main_model() -> MistralChat:
    """LLM that drives the conversation and calls tools/skills."""
    settings = get_settings()
    return MistralChat(
        id=settings.llm_model_id,
        api_key=settings.llm_api_key,
        temperature=settings.llm_temperature,
    )


def build_parser_model() -> MistralChat:
    """LLM that extracts the structured output. Uses temperature 0 for stability."""
    settings = get_settings()
    return MistralChat(
        id=settings.llm_model_id,
        api_key=settings.llm_api_key,
        temperature=0.0,
    )
