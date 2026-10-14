"""FastAPI application entrypoint for StudyQuiz AI."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .db import init_db

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Create tables and clean up on shutdown."""
    init_db()
    yield


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="RAG-based quiz generation and AI evaluation for students.",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from .api import attempts, documents, health, quizzes

    app.include_router(health.router, prefix=settings.api_prefix)
    app.include_router(documents.router, prefix=settings.api_prefix)
    app.include_router(quizzes.router, prefix=settings.api_prefix)
    app.include_router(attempts.router, prefix=settings.api_prefix)

    @app.get("/", summary="Service metadata")
    def root() -> dict:
        return {
            "name": settings.app_name,
            "version": settings.app_version,
            "docs": "/docs",
            "health": f"{settings.api_prefix}/health",
        }

    return app


app = create_app()