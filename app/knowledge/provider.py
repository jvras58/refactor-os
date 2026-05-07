"""PgVector-backed knowledge base for the design pattern reference corpus."""
from __future__ import annotations

from functools import lru_cache

from agno.knowledge.knowledge import Knowledge
from agno.vectordb.pgvector import PgVector

from app.core.config import get_settings
from app.db.session import get_db


@lru_cache
def get_pattern_knowledge() -> Knowledge:
    """Return a Knowledge instance backed by PgVector for the 5 design patterns."""
    settings = get_settings()
    vector_db = PgVector(
        table_name=settings.knowledge_table,
        db_url=settings.db_url,
    )
    return Knowledge(
        name="design-patterns-kb",
        description="Estrutura canônica e exemplos dos 5 design patterns suportados.",
        vector_db=vector_db,
        contents_db=get_db(),
    )
