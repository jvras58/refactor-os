"""Centralized environment configuration via Pydantic settings."""
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "refactor-os"
    app_env: str = Field(default="development")
    log_level: str = Field(default="INFO")

    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)

    llm_api_key: str = Field(default="")
    llm_model_id: str = Field(default="mistral-medium-latest")
    llm_temperature: float = Field(default=0.2, ge=0.0, le=1.0)

    skills_dir: Path = Field(default=PROJECT_ROOT / "app" / "skills")

    huggingface_api_key: str = Field(default="", description="Token HF para embeddings via Inference API (gratuito).")
    embedding_model_id: str = Field(default="BAAI/bge-small-en-v1.5")

    db_url: str = Field(
        default="postgresql+psycopg://ai:ai@localhost:5532/ai",
        description="PostgreSQL + pgvector connection string used by Agno.",
    )

    knowledge_table: str = Field(default="design_patterns_kb")

    patterns_dir: Path = Field(default=PROJECT_ROOT / "app" / "knowledge" / "patterns")
    solutions_dir: Path = Field(
        default=PROJECT_ROOT / "app" / "knowledge" / "solutions",
        description="Corpus autoral de soluções problema→refatoração, indexado no pgvector.",
    )
    dataset_dir: Path = Field(default=PROJECT_ROOT / "dataset")

    max_reflection_iterations: int = Field(default=3, ge=1, le=10)


@lru_cache
def get_settings() -> Settings:
    return Settings()
