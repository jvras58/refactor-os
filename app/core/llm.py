"""LLM model builders shared by all agents.

We expose a **main model** (used for tool/skill calling) and a **parser model**
(used by Agno to extract the structured output from the main model's response).

The split exists because Mistral's JSON-mode is incompatible with tool/skill
calls in the same request — forcing both leads to empty responses. Agno's
``parser_model`` parameter delegates the JSON extraction to a second call where
no tools are exposed, which is the supported workaround.

The backend is selected by ``settings.llm_provider``:
- ``mistral`` → Mistral API online (``MistralChat``);
- ``ollama``  → modelo local servido pelo Ollama (``Ollama``), ex.: ``mistral``
  ou ``qwen2.5``. Use para comparar modelos locais no lugar da API.
"""
from __future__ import annotations

from agno.models.mistral import MistralChat
from agno.models.ollama import Ollama

from app.core.config import get_settings


def _build_model(temperature: float) -> MistralChat | Ollama:
    settings = get_settings()
    if settings.llm_provider == "ollama":
        return Ollama(
            id=settings.llm_model_id,
            host=settings.ollama_base_url,
            options={"temperature": temperature},
        )
    return MistralChat(
        id=settings.llm_model_id,
        api_key=settings.llm_api_key,
        temperature=temperature,
    )


def build_main_model() -> MistralChat | Ollama:
    """LLM that drives the conversation and calls tools/skills."""
    return _build_model(get_settings().llm_temperature)


def build_parser_model() -> MistralChat | Ollama:
    """LLM that extracts the structured output. Uses temperature 0 for stability."""
    return _build_model(0.0)
