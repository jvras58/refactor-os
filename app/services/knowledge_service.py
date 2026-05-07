"""Batch loader for the design pattern knowledge base."""
from __future__ import annotations

import logging
from pathlib import Path

from app.core.config import get_settings
from app.knowledge.provider import get_pattern_knowledge

logger = logging.getLogger(__name__)


def load_patterns_into_kb() -> int:
    """Index every markdown file under `patterns_dir` into PgVector.

    Returns the number of files successfully loaded.
    """
    settings = get_settings()
    knowledge = get_pattern_knowledge()
    patterns_dir: Path = settings.patterns_dir
    if not patterns_dir.is_dir():
        raise FileNotFoundError(f"patterns dir not found: {patterns_dir}")

    files = sorted(patterns_dir.glob("*.md"))
    for path in files:
        logger.info("Indexing pattern doc: %s", path.name)
        knowledge.add_content(path=str(path))
    return len(files)
