"""Shared Postgres connection used by Agno (sessions, memories, traces).

No vector storage — design pattern knowledge agora é injetado via Agno Skills
(``app/skills/``), não mais via embeddings em pgvector.
"""
from functools import lru_cache

from agno.db.postgres import PostgresDb

from app.core.config import get_settings


@lru_cache
def get_db() -> PostgresDb:
    settings = get_settings()
    return PostgresDb(id="refactor-db", db_url=settings.db_url)
