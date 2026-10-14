"""Shared test fixtures.

Environment variables are set *before* the app is imported (pydantic-settings
reads them on first use), and the test database / vector store are wiped at the
start of every session so schema changes are picked up automatically.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_DATABASE_FILE = _BACKEND_DIR / "data" / "test_studyquiz.db"
_CHROMA_DIR = _BACKEND_DIR / "data" / "test_chroma"

# Reset on-disk state from any previous run.
_DATABASE_FILE.unlink(missing_ok=True)
shutil.rmtree(_CHROMA_DIR, ignore_errors=True)

os.environ.setdefault("DATABASE_URL", "sqlite:///./data/test_studyquiz.db")
os.environ.setdefault("CHROMA_DIR", "./data/test_chroma")

from fastapi.testclient import TestClient  # noqa: E402

import pytest  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture()
def client() -> TestClient:
    """A TestClient wired to the real FastAPI app (lifespan runs)."""
    with TestClient(app) as test_client:
        yield test_client
