"""Health endpoint: database, LLM modes, and embedding backend."""

from __future__ import annotations

from fastapi import APIRouter

from ..services.health_service import HealthReport, build_health_report

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=HealthReport, summary="Report health of the database, Ollama, and Gemini")
def get_health() -> HealthReport:
    """Return availability for the DB, both LLM modes, and embeddings.

    This endpoint never 500s: unavailability is reported in the payload.
    """
    return build_health_report()