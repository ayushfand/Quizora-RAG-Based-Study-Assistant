"""Application configuration, loaded from environment variables and `.env` files.

Settings are typed with pydantic-settings. The first `.env` file that exists
wins; backend/.env takes precedence over the repository root .env. Every value
can also be supplied as a real environment variable.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Typed application settings.

    All secret and machine-specific values live here; never hard-code them.
    """

    model_config = SettingsConfigDict(
        env_file=(BACKEND_DIR / ".env", BACKEND_DIR.parent / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Application -------------------------------------------------------
    app_name: str = "StudyQuiz AI"
    app_version: str = "0.1.0"
    api_prefix: str = "/api"

    # --- Storage -----------------------------------------------------------
    database_url: str = "sqlite:///./data/studyquiz.db"
    chroma_dir: str = "./data/chroma"
    max_upload_mb: int = 50

    # --- LLM mode ----------------------------------------------------------
    default_llm_mode: Literal["local", "gemini"] = "local"

    # --- Ollama ------------------------------------------------------------
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b-instruct"
    ollama_embed_model: str = "nomic-embed-text"

    # --- Gemini ------------------------------------------------------------
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.0-flash"

    # --- LLM behaviour -----------------------------------------------------
    llm_timeout_seconds: float = 180.0
    llm_max_json_attempts: int = 3

    # --- CORS --------------------------------------------------------------
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        """Comma-separated origin list from config, trimmed and non-empty."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @field_validator("max_upload_mb")
    @classmethod
    def _max_upload_must_be_positive(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("MAX_UPLOAD_MB must be a positive integer")
        return value


@lru_cache
def get_settings() -> Settings:
    """Return the cached Settings singleton."""
    return Settings()