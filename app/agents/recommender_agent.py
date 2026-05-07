"""Recommender Agent — proposes a refactored version applying a Design Pattern."""
from __future__ import annotations

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.knowledge import KnowledgeTools

from app.core.config import get_settings
from app.core.prompts import RECOMMENDER_INSTRUCTIONS
from app.core.schemas import RefactoringProposal
from app.db.session import get_db
from app.knowledge.provider import get_pattern_knowledge
from app.tools.pattern_registry import design_pattern_reference_tool


def build_recommender_agent() -> Agent:
    settings = get_settings()
    return Agent(
        name="Recommender Agent",
        id="recommender-agent",
        role="Sugere o Design Pattern adequado e produz o código refatorado.",
        model=OpenAIChat(id=settings.llm_model_id),
        db=get_db(),
        tools=[
            design_pattern_reference_tool,
            KnowledgeTools(knowledge=get_pattern_knowledge()),
        ],
        instructions=RECOMMENDER_INSTRUCTIONS,
        response_model=RefactoringProposal,
        markdown=False,
    )
