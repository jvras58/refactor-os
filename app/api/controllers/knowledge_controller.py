"""Knowledge controller for knowledge sync endpoints."""
from __future__ import annotations

from app.services.knowledge_service import load_patterns_into_kb


def sync_knowledge() -> dict[str, int]:
    loaded = load_patterns_into_kb()
    return {"loaded": loaded}