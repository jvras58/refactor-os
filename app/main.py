"""ASGI entry point — wires AgentOS, FastAPI routes and the multi-agent pipeline."""
from __future__ import annotations

import logging

from agno.os import AgentOS

from app.agents import (
    build_critic_agent,
    build_detector_agent,
    build_recommender_agent,
    build_refactor_team,
)
from app.api.routes import router
from app.core.config import get_settings


def _configure_logging(level: str) -> None:
    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def create_app():
    settings = get_settings()
    _configure_logging(settings.log_level)

    detector = build_detector_agent()
    recommender = build_recommender_agent()
    critic = build_critic_agent()
    team = build_refactor_team()

    agent_os = AgentOS(
        description="Sistema multi-agente determinístico de refatoração orientada por Design Patterns.",
        agents=[detector, recommender, critic],
        teams=[team],
    )
    fastapi_app = agent_os.get_app()
    fastapi_app.include_router(router)
    return agent_os, fastapi_app


agent_os, app = create_app()


if __name__ == "__main__":
    settings = get_settings()
    agent_os.serve(app="app.main:app", host=settings.api_host, port=settings.api_port, reload=True)
