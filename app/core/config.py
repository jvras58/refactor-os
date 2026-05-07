"""Centralized environment configuration via Pydantic settings."""
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "refactor-os"
    app_env: str = Field(default="development")
    log_level: str = Field(default="INFO")

    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)

    openai_api_key: str = Field(default="")
    llm_model_id: str = Field(default="gpt-4o")

    db_url: str = Field(
        default="postgresql+psycopg://ai:ai@localhost:5532/ai",
        description="PostgreSQL + pgvector connection string used by Agno.",
    )

    knowledge_table: str = Field(default="design_patterns_kb")
    patterns_dir: Path = Field(default=PROJECT_ROOT / "app" / "knowledge" / "patterns")
    dataset_dir: Path = Field(default=PROJECT_ROOT / "dataset")

    max_reflection_iterations: int = Field(default=3, ge=1, le=10)


@lru_cache
def get_settings() -> Settings:
    return Settings()
