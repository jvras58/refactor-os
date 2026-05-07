"""Recommender Agent — proposes a refactored version applying a Design Pattern."""
from __future__ import annotations

from agno.agent import Agent
from agno.models.groq import Groq

from app.core.config import get_settings
from app.core.prompts import RECOMMENDER_INSTRUCTIONS
from app.core.schemas import RefactoringProposal
from app.db.session import get_db


def build_recommender_agent() -> Agent:
    settings = get_settings()
    return Agent(
        name="Recommender Agent",
        id="recommender-agent",
        role="Sugere o Design Pattern adequado e produz o código refatorado.",
        model=Groq(api_key=settings.groq_api_key, id=settings.llm_model_id),
        db=get_db(),
        instructions=RECOMMENDER_INSTRUCTIONS,
        output_schema=RefactoringProposal,
        markdown=False,
    )
