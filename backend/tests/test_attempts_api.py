"""API smoke tests for the attempts (evaluation) endpoints.

The LLM is replaced with a fake provider so the tests stay deterministic and do
not require Ollama or Gemini.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.api import attempts as attempts_api
from app.db import SessionLocal
from app.models.entities import Document, DocumentStatus, Question, Quiz, QuizStatus

from .fakes import FakeProvider


@pytest.fixture()
def seeded_quiz(client: TestClient) -> dict:
    """Insert a ready document + quiz with one MCQ and one open question."""
    db = SessionLocal()
    try:
        document = Document(
            original_filename="biology.pdf",
            stored_path=None,
            content_type="application/pdf",
            file_size=1024,
            status=DocumentStatus.READY.value,
            source_type="pdf",
            num_chunks=2,
            embedding_model="ollama/nomic-embed-text",
        )
        db.add(document)
        db.flush()

        quiz = Quiz(
            document_id=document.id,
            requested_num_questions=2,
            question_types=["mcq", "short_answer"],
            difficulty="easy",
            topic=None,
            mode="local",
            status=QuizStatus.READY.value,
        )
        db.add(quiz)
        db.flush()

        mcq = Question(
            quiz_id=quiz.id,
            position=1,
            type="mcq",
            difficulty="easy",
            text="Where does photosynthesis take place?",
            options=["Chloroplasts", "Mitochondria", "Ribosomes", "Nucleus"],
            correct_option=0,
            explanation="Chloroplasts are the site of photosynthesis.",
            key_points=[],
            source_chunk_ids=["doc:0"],
            source_page_numbers=[1],
        )
        open_q = Question(
            quiz_id=quiz.id,
            position=2,
            type="short_answer",
            difficulty="medium",
            text="What does the Calvin cycle produce?",
            options=None,
            correct_option=None,
            reference_answer="The Calvin cycle uses CO2 to produce glucose.",
            key_points=["uses carbon dioxide", "produces glucose"],
            explanation=None,
            source_chunk_ids=["doc:1"],
            source_page_numbers=[2],
        )
        db.add_all([mcq, open_q])
        db.commit()
        return {"quiz_id": quiz.id, "mcq_id": mcq.id, "open_id": open_q.id}
    finally:
        db.close()


def _fake_provider(monkeypatch: pytest.MonkeyPatch, responses: list[str]) -> FakeProvider:
    provider = FakeProvider(responses)
    monkeypatch.setattr(attempts_api, "get_provider", lambda mode=None: provider)
    return provider


def _judge_response(score: float) -> str:
    return json.dumps(
        {
            "score": score,
            "covered_points": ["uses carbon dioxide"],
            "missed_points": ["produces glucose"],
            "feedback": "Partly correct; say more about glucose.",
            "model_answer": "The Calvin cycle fixes CO2 into glucose.",
        }
    )


def test_submit_attempt_grades_all_questions(client: TestClient, seeded_quiz: dict, monkeypatch) -> None:
    provider = _fake_provider(monkeypatch, [_judge_response(7.0)])

    response = client.post(
        "/api/attempts",
        json={
            "quiz_id": seeded_quiz["quiz_id"],
            "answers": [
                {"question_id": seeded_quiz["mcq_id"], "selected_option": 0},
                {"question_id": seeded_quiz["open_id"], "answer_text": "CO2 is used."},
            ],
        },
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["quiz_id"] == seeded_quiz["quiz_id"]
    assert body["max_score"] == 20.0
    assert body["total_score"] == 17.0  # 10 (mcq) + 7 (open)
    assert len(provider.calls) == 1  # only the open question hits the LLM

    by_id = {a["question_id"]: a for a in body["answers"]}
    mcq = by_id[seeded_quiz["mcq_id"]]
    assert mcq["score"] == 10.0
    assert mcq["verdict"] == "correct"
    assert mcq["selected_option"] == 0
    assert mcq["user_answer"] == "Chloroplasts"

    open_answer = by_id[seeded_quiz["open_id"]]
    assert open_answer["score"] == 7.0
    assert open_answer["verdict"] == "partial"
    assert open_answer["covered_points"] == ["uses carbon dioxide"]
    assert open_answer["model_answer"] == "The Calvin cycle fixes CO2 into glucose."


def test_submit_attempt_with_missing_answers_scores_zero_without_llm(
    client: TestClient, seeded_quiz: dict, monkeypatch
) -> None:
    provider = _fake_provider(monkeypatch, [])

    response = client.post("/api/attempts", json={"quiz_id": seeded_quiz["quiz_id"], "answers": []})

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["total_score"] == 0.0
    assert body["max_score"] == 20.0
    assert {a["verdict"] for a in body["answers"]} == {"blank"}
    assert provider.calls == []


def test_submit_attempt_unknown_quiz_returns_400(client: TestClient, monkeypatch) -> None:
    _fake_provider(monkeypatch, [])
    response = client.post("/api/attempts", json={"quiz_id": 987654, "answers": []})
    assert response.status_code == 400
    assert "not found" in response.json()["detail"].lower()


def test_submit_attempt_rejects_foreign_question(client: TestClient, seeded_quiz: dict, monkeypatch) -> None:
    _fake_provider(monkeypatch, [])
    response = client.post(
        "/api/attempts",
        json={"quiz_id": seeded_quiz["quiz_id"], "answers": [{"question_id": 999999, "answer_text": "hi"}]},
    )
    assert response.status_code == 400
    assert "not part of this quiz" in response.json()["detail"]


def test_list_and_get_attempts(client: TestClient, seeded_quiz: dict, monkeypatch) -> None:
    _fake_provider(monkeypatch, [_judge_response(4.0)])
    created = client.post(
        "/api/attempts",
        json={
            "quiz_id": seeded_quiz["quiz_id"],
            "answers": [
                {"question_id": seeded_quiz["mcq_id"], "selected_option": 1},
                {"question_id": seeded_quiz["open_id"], "answer_text": "not much"},
            ],
        },
    )
    assert created.status_code == 201
    attempt_id = created.json()["id"]

    listed = client.get("/api/attempts", params={"quiz_id": seeded_quiz["quiz_id"]})
    assert listed.status_code == 200
    assert any(row["id"] == attempt_id for row in listed.json())

    fetched = client.get(f"/api/attempts/{attempt_id}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == attempt_id

    missing = client.get("/api/attempts/999999")
    assert missing.status_code == 404


def test_delete_attempt(client: TestClient, seeded_quiz: dict, monkeypatch) -> None:
    _fake_provider(monkeypatch, [_judge_response(5.0)])
    created = client.post(
        "/api/attempts",
        json={
            "quiz_id": seeded_quiz["quiz_id"],
            "answers": [
                {"question_id": seeded_quiz["mcq_id"], "selected_option": 0},
            ],
        },
    )
    assert created.status_code == 201
    attempt_id = created.json()["id"]

    del_resp = client.delete(f"/api/attempts/{attempt_id}")
    assert del_resp.status_code == 204

    # Now verify it's gone
    assert client.get(f"/api/attempts/{attempt_id}").status_code == 404