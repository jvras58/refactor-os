"""Retry helpers for transient LLM provider errors (rate limits, capacity) and
schema-validation failures of the parser_model."""
from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

logger = logging.getLogger(__name__)

RETRYABLE_HINTS: tuple[str, ...] = (
    "rate_limited",
    "rate limit",
    "429",
    "too many requests",
    "service_tier_capacity",
)

# Throttle global para evitar estourar rate limit em avaliações locais.
# Com mistral-medium-latest na conta gratuita, o limite é bem baixo.
MIN_SECONDS_BETWEEN_LLM_CALLS = 20.0

_LLM_CALL_LOCK = asyncio.Lock()
_LAST_LLM_CALL_AT = 0.0


def is_retryable_error(exc: BaseException) -> bool:
    """Return True when the exception message looks like a transient rate-limit."""
    message = str(exc).lower()
    return any(hint in message for hint in RETRYABLE_HINTS)


def is_retryable_content(content: Any) -> bool:
    """Return True when the model returned a textual rate-limit error."""
    message = str(content).lower()
    return any(hint in message for hint in RETRYABLE_HINTS)


async def _wait_for_llm_slot(label: str) -> None:
    """Serialize LLM calls and wait between them to respect provider limits."""
    global _LAST_LLM_CALL_AT

    async with _LLM_CALL_LOCK:
        now = time.monotonic()
        elapsed = now - _LAST_LLM_CALL_AT
        wait_time = MIN_SECONDS_BETWEEN_LLM_CALLS - elapsed

        if wait_time > 0:
            logger.info(
                "%s waiting %.1fs before next LLM call to avoid rate limit",
                label,
                wait_time,
            )
            await asyncio.sleep(wait_time)

        _LAST_LLM_CALL_AT = time.monotonic()


async def arun_with_backoff[T](
    func: Callable[..., Awaitable[T]],
    /,
    *args: object,
    label: str,
    attempts: int = 4,
    base_delay: float = 30.0,
    **kwargs: object,
) -> T:
    """Call func(*args, **kwargs) retrying transient rate-limit errors.

    The wait between retries grows as base_delay * 2 ** (attempt - 1).
    A global throttle is applied before every LLM call to avoid hitting
    free-tier provider limits during local evaluation.
    """
    attempt = 0

    while True:
        attempt += 1

        try:
            await _wait_for_llm_slot(label)
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
    attempts: int = 3,
) -> T:
    """Call agent_arun(prompt) and return response.content cast to schema.

    Handles both layers of transient failures in the Mistral pipeline:
      * rate-limit / capacity errors raised as exceptions;
      * parser_model occasionally returning a raw string instead of the expected
        Pydantic instance;
      * provider errors returned as text content, e.g. Status 429.
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

        if attempt < attempts and is_retryable_content(content):
            delay = 30.0 * (2 ** (attempt - 1))
            logger.warning(
                "%s received textual rate-limit response - sleeping %.1fs",
                label,
                delay,
            )
            await asyncio.sleep(delay)

    raise ValueError(
        f"{label} retornou tipo inesperado após {attempts} tentativas: "
        f"{type(last_content).__name__} — {last_content!r}"
    )