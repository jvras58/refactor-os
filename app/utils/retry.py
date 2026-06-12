"""Retry helpers for transient LLM provider errors (rate limits, capacity) and
schema-validation failures of the parser_model."""
from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

logger = logging.getLogger(__name__)

RETRYABLE_HINTS: tuple[str, ...] = (
    "rate_limited",
    "rate limit",
    "429",
    "service_tier_capacity",
)


def is_retryable_error(exc: BaseException) -> bool:
    """Return ``True`` when the exception message looks like a transient rate-limit."""
    message = str(exc).lower()
    return any(hint in message for hint in RETRYABLE_HINTS)


async def arun_with_backoff[T](
    func: Callable[..., Awaitable[T]],
    /,
    *args: object,
    label: str,
    attempts: int = 4,
    base_delay: float = 2.0,
    **kwargs: object,
) -> T:
    """Call ``func(*args, **kwargs)`` retrying transient rate-limit errors.

    The wait between retries grows as ``base_delay * 2 ** (attempt - 1)``. The
    original exception is re-raised when ``attempts`` is exhausted or when
    :func:`is_retryable_error` returns ``False``.
    """
    attempt = 0
    while True:
        attempt += 1
        try:
            return await func(*args, **kwargs)
        except Exception as exc:
            if attempt >= attempts or not is_retryable_error(exc):
                raise
            delay = base_delay * (2 ** (attempt - 1))
            logger.warning(
                "%s hit rate limit (attempt %d/%d) - sleeping %.1fs",
                label,
                attempt,
                attempts,
                delay,
            )
            await asyncio.sleep(delay)


async def arun_typed[T](
    agent_arun: Callable[..., Awaitable[Any]],
    prompt: str,
    *,
    schema: type[T],
    label: str,
    attempts: int = 2,
) -> T:
    """Call ``agent_arun(prompt)`` and return ``response.content`` cast to ``schema``.

    Handles both layers of transient failures in the Mistral pipeline:
      * rate-limit / capacity errors (via :func:`arun_with_backoff`);
      * parser_model occasionally returning a raw string instead of the expected
        Pydantic instance — retried up to ``attempts`` times before raising.

    Raises ``ValueError`` with the last observed content if no attempt validates.
    """
    last_content: Any = None
    for attempt in range(1, attempts + 1):
        response = await arun_with_backoff(agent_arun, prompt, label=label)
        content = response.content
        if isinstance(content, schema):
            return content
        last_content = content
        logger.warning(
            "%s returned non-%s content (attempt %d/%d): %r",
            label,
            schema.__name__,
            attempt,
            attempts,
            content,
        )
    raise ValueError(
        f"{label} retornou tipo inesperado após {attempts} tentativas: "
        f"{type(last_content).__name__} — {last_content!r}"
    )
