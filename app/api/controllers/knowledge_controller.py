"""Knowledge controller — indexes the solution corpus into pgvector."""
from __future__ import annotations

from app.knowledge.provider import sync_knowledge


async def sync() -> dict[str, object]:
    """Index app/knowledge/solutions/ into the pgvector knowledge table."""
    counts = await sync_knowledge()
    return {"status": "ok", "indexed": counts}
