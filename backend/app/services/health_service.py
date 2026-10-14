"""Health reporting for the database, LLM providers, and embeddings.

Used by GET /api/health. Never raises: every subsystem reports availability
and an error message instead, so the endpoint always returns HTTP 200 with a
structured payload the frontend can render.
"""

from __future__ import annotations

from pydantic import BaseModel

from ..config import get_settings
from ..db import ping_db
from ..llm.base import ProviderHealth
from ..llm.gemini_provider import GeminiProvider
from ..llm.ollama_provider import OllamaProvider


class DatabaseHealth(BaseModel):
    """Database availability report."""

    ok: bool


class HealthReport(BaseModel):
    """Aggregate health report returned by /api/health."""

    status: str
    database: DatabaseHealth
    llm: dict[str, ProviderHealth]
    embeddings: ProviderHealth


def build_health_report() -> HealthReport:
    """Probe the database, both LLM modes, and the embedding backend."""
    settings = get_settings()

    database_ok = ping_db()

    local = OllamaProvider(
        base_url=settings.ollama_base_url, model=settings.ollama_model, timeout_seconds=5
    ).check_health()

    embeddings = OllamaProvider(
        base_url=settings.ollama_base_url, model=settings.ollama_embed_model, timeout_seconds=5
    ).check_health()
    embeddings = embeddings.model_copy(update={"mode": "ollama-embed"})

    if settings.gemini_api_key:
        gemini = GeminiProvider(
            api_key=settings.gemini_api_key, model=settings.gemini_model, timeout_seconds=8
        ).check_health()
    else:
        gemini = ProviderHealth(
            mode="gemini",
            available=False,
            default_model=settings.gemini_model,
            error="GEMINI_API_KEY is not set in backend/.env. Gemini mode is unavailable.",
        )

    llm = {"local": local, "gemini": gemini}
    any_provider_ready = local.available or gemini.available
    status = "ok" if database_ok and any_provider_ready else "degraded"
    return HealthReport(status=status, database=DatabaseHealth(ok=database_ok), llm=llm, embeddings=embeddings)