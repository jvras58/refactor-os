"""Coordinator Team aggregating Detector + Recommender + Critic."""
from __future__ import annotations

from agno.models.openai import OpenAIChat
from agno.team import Team

from app.agents.critic_agent import build_critic_agent
from app.agents.detector_agent import build_detector_agent
from app.agents.recommender_agent import build_recommender_agent
from app.core.config import get_settings
from app.core.prompts import TEAM_INSTRUCTIONS
from app.db.session import get_db


def build_refactor_team() -> Team:
    settings = get_settings()
    return Team(
        id="refactor-team",
        name="Refactoring Team",
        model=OpenAIChat(id=settings.llm_model_id),
        db=get_db(),
        members=[
            build_detector_agent(),
            build_recommender_agent(),
            build_critic_agent(),
        ],
        instructions=TEAM_INSTRUCTIONS,
    )
