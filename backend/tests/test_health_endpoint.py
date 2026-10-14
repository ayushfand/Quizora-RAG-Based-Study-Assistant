"""API smoke tests: health endpoint, root endpoint, and DB schema creation."""

from __future__ import annotations

from sqlalchemy import inspect

from app.db import engine, init_db


def test_tables_are_created() -> None:
    init_db()
    names = set(inspect(engine).get_table_names())
    for table in {"documents", "quizzes", "questions", "attempts", "attempt_answers"}:
        assert table in names, f"missing table {table}"


def test_root_endpoint(client) -> None:
    response = client.get("/")
    assert response.status_code == 200
    payload = response.json()
    assert payload["name"] == "StudyQuiz AI"
    assert payload["health"] == "/api/health"


def test_health_endpoint_returns_structured_report(client) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] in {"ok", "degraded"}
    assert "ok" in payload["database"]
    assert {"local", "gemini"} <= set(payload["llm"].keys())
    assert "embeddings" in payload
    for mode in ("local", "gemini"):
        report = payload["llm"][mode]
        assert set(report) >= {"available", "models", "default_model", "default_model_available", "error"}


def test_unknown_route_returns_404(client) -> None:
    assert client.get("/api/nope").status_code == 404