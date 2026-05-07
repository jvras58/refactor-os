"""Shared Postgres + pgvector connection used by Agno (sessions, memories, traces)."""
from functools import lru_cache

from agno.db.postgres import PostgresDb

from app.core.config import get_settings


@lru_cache
def get_db() -> PostgresDb:
    settings = get_settings()
    return PostgresDb(id="refactor-db", db_url=settings.db_url)
