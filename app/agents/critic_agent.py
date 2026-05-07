"""Critic / Reflection Agent — validates syntax and business-logic preservation."""
from __future__ import annotations

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.shell import ShellTools

from app.core.config import get_settings
from app.core.prompts import CRITIC_INSTRUCTIONS
from app.core.schemas import ReflectionReview
from app.db.session import get_db
from app.tools.diff_tools import diff_generator_tool
from app.tools.syntax_tools import syntax_checker_tool


def build_critic_agent() -> Agent:
    settings = get_settings()
    return Agent(
        name="Critic Agent",
        agent_id="critic-agent",
        role="Valida sintaxe e preservação da lógica do código refatorado.",
        model=OpenAIChat(id=settings.llm_model_id),
        db=get_db(),
        tools=[syntax_checker_tool, diff_generator_tool, ShellTools()],
        instructions=CRITIC_INSTRUCTIONS,
        response_model=ReflectionReview,
        markdown=False,
    )
