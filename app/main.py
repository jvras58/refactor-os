"""ASGI entry point — FastAPI app exposing the multi-agent refactoring pipeline."""
from __future__ import annotations

import logging

from fastapi import FastAPI

from app.api.routes import router
from app.core.config import get_settings


def _configure_logging(level: str) -> None:
    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def create_app() -> FastAPI:
    settings = get_settings()
    _configure_logging(settings.log_level)

    fastapi_app = FastAPI(
        title="refactor-os",
        description="Sistema multi-agente determinístico de refatoração orientada por Design Patterns.",
        version="0.1.0",
    )
    fastapi_app.include_router(router)
    return fastapi_app


app = create_app()


@app.get("/")
def health() -> dict[str, str]:
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run("app.main:app", host=settings.api_host, port=settings.api_port, reload=True)
