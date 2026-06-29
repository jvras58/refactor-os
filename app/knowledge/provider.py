"""PgVector-backed knowledge base for the design pattern reference corpus.

Uses HuggingfaceCustomEmbedder (BAAI/bge-small-en-v1.5, 384 dims) via the HF
Inference API gratuita — sem compilação Rust, sem provedor pago.
Requer HUGGINGFACE_API_KEY no .env (token gratuito em huggingface.co/settings/tokens).

A base reúne dois corpora no mesmo índice pgvector:
- ``patterns/`` — estrutura canônica (intent, regras) de cada pattern;
- ``solutions/`` — exemplos autorais problema→refatoração (distintos do dataset
  de avaliação, para não vazar ground truth).

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
def get_pattern_knowledge() -> Knowledge:
    """Return a Knowledge instance backed by PgVector for the 5 design patterns."""
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
        name="design-patterns-kb",
        description="Estrutura canônica e exemplos dos 5 design patterns suportados.",
        vector_db=vector_db,
        contents_db=get_db(),
    )


async def sync_knowledge() -> dict[str, int]:
    """Index the patterns and solutions corpora into pgvector (idempotent upsert).

    Returns the number of markdown files found per corpus. Re-running upserts by
    content name, so it is safe to call on boot or via the sync endpoint.
    """
    settings = get_settings()
    knowledge = get_pattern_knowledge()

    counts: dict[str, int] = {}
    for label, directory, metadata in (
        ("patterns", settings.patterns_dir, {"corpus": "pattern"}),
        ("solutions", settings.solutions_dir, {"corpus": "solution"}),
    ):
        files = sorted(directory.glob("*.md")) if directory.exists() else []
        counts[label] = len(files)
        if not files:
            logger.warning("Knowledge corpus '%s' is empty at %s", label, directory)
            continue
        await knowledge.add_content_async(
            path=str(directory),
            metadata=metadata,
            upsert=True,
        )
        logger.info("Indexed %d '%s' documents into pgvector", len(files), label)

    return counts