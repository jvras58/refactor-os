"""PgVector-backed knowledge base of refactoring solution examples.

Uses HuggingfaceCustomEmbedder (BAAI/bge-small-en-v1.5, 384 dims) via the HF
Inference API gratuita — sem compilação Rust, sem provedor pago.
Requer HUGGINGFACE_API_KEY no .env (token gratuito em huggingface.co/settings/tokens).

Indexa apenas ``app/knowledge/solutions/*.md`` — exemplos autorais problema→
refatoração, distintos do dataset de avaliação (sem vazar ground truth). A
estrutura canônica de cada pattern (intent/regras) vive nas Agno Skills
(``app/skills/``), então não é reindexada aqui para evitar duplicação.

A tabela só fica populada após ``sync_knowledge`` (endpoint ``POST /knowledge/sync``).
"""
from __future__ import annotations

import logging
from functools import lru_cache

from agno.knowledge.embedder.huggingface import HuggingfaceCustomEmbedder
from agno.knowledge.knowledge import Knowledge
from agno.vectordb.pgvector import PgVector

from app.core.config import get_settings
from app.db.session import get_db

logger = logging.getLogger(__name__)


@lru_cache
def get_solution_knowledge() -> Knowledge:
    """Return a Knowledge instance backed by PgVector for the solution corpus."""
    settings = get_settings()
    embedder = HuggingfaceCustomEmbedder(
        id=settings.embedding_model_id,
        dimensions=384,
        api_key=settings.huggingface_api_key or None,
    )
    vector_db = PgVector(
        table_name=settings.knowledge_table,
        db_url=settings.db_url,
        embedder=embedder,
    )
    return Knowledge(
        name="refactoring-solutions-kb",
        description="Exemplos autorais problema→refatoração dos 5 design patterns suportados.",
        vector_db=vector_db,
        contents_db=get_db(),
    )


async def sync_knowledge() -> dict[str, int]:
    """Index the solution corpus into pgvector (idempotent upsert by content name).

    Returns the number of markdown files indexed. Safe to re-run.
    """
    settings = get_settings()
    knowledge = get_solution_knowledge()

    directory = settings.solutions_dir
    files = sorted(directory.glob("*.md")) if directory.exists() else []
    if not files:
        logger.warning("Solution corpus is empty at %s", directory)
        return {"solutions": 0}

    await knowledge.add_content_async(
        path=str(directory),
        metadata={"corpus": "solution"},
        upsert=True,
    )
    logger.info("Indexed %d solution documents into pgvector", len(files))
    return {"solutions": len(files)}