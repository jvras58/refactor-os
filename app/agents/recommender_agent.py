"""Recommender Agent — proposes a refactored version applying a Design Pattern."""
from __future__ import annotations

from pathlib import Path

from agno.agent import Agent
from agno.skills import LocalSkills, Skills
from agno.tools.knowledge import KnowledgeTools

from app.core.llm import build_main_model, build_parser_model
from app.core.prompts import RECOMMENDER_INSTRUCTIONS
from app.core.schemas import RefactoringProposal
from app.db.session import get_db
from app.knowledge.provider import get_solution_knowledge

SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills"


def build_recommender_agent() -> Agent:
    return Agent(
        name="Recommender Agent",
        id="recommender-agent",
        role="Sugere o Design Pattern adequado e produz o código refatorado.",
        model=build_main_model(),
        parser_model=build_parser_model(),
        db=get_db(),
        tools=[
            # Recupera exemplos problema→refatoração do corpus de soluções (search_knowledge).
            KnowledgeTools(
                knowledge=get_solution_knowledge(),
                enable_think=False,
                enable_analyze=False,
            ),
        ],
        skills=Skills(loaders=[LocalSkills(str(SKILLS_DIR))]),
        instructions=RECOMMENDER_INSTRUCTIONS,
        output_schema=RefactoringProposal,
        markdown=False,
    )
