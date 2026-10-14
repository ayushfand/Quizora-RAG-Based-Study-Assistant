"""Tests for the batch quez-generation logic (fake provider, no Ollama/Gemini)."""

from __future__ import annotations

import json

import pytest

from app.llm.errors import LLMConnectionError
from app.rag.vectorstore import StoredChunk
from app.schemas.generated import GeneratedQuestion
from app.services.quiz_generator import generate_questions

from .fakes import FakeProvider


def _chunk(text: str, page: int, index: int) -> StoredChunk:
    return StoredChunk(text=text, chunk_id=f"doc_1:{index}", page_number=page, chunk_index=index, source_name="x.pdf", score=0.0)


CHUNKS = [
    _chunk("Photosynthesis converts light into chemical energy in chloroplasts.", page=1, index=0),
    _chunk("The Calvin cycle uses carbon dioxide to produce glucose.", page=1, index=1),
    _chunk("Water is split during the light reactions, releasing oxygen.", page=2, index=2),
    _chunk("Enzymes control each step of cellular respiration.", page=3, index=3),
]


def _mcq(text: str) -> dict:
    return {
        "type": "mcq",
        "difficulty": "easy",
        "text": text,
        "options": ["A is right", "B", "C", "D"],
        "correct_option": 0,
        "explanation": "A is supported by the source.",
    }


def _open_q(text: str, kind: str = "short_answer") -> dict:
    return {
        "type": kind,
        "difficulty": "medium",
        "text": text,
        "reference_answer": "A complete reference answer about the topic.",
        "key_points": ["k1", "k2", "k3"],
    }


def test_generate_questions_single_batch() -> None:
    batch = [_mcq("Where does photosynthesis occur?"), _open_q("Explain the Calvin cycle.")]
    provider = FakeProvider([json.dumps({"questions": batch})])
    questions = generate_questions(
        provider=provider,
        chunks=CHUNKS,
        num_questions=2,
        question_types=["mcq", "short_answer"],
        difficulty="easy",
        topic=None,
    )
    assert len(questions) == 2
    assert all(isinstance(q, GeneratedQuestion) for q in questions)
    assert len(provider.calls) == 1
    # The prompt must include the source content.
    assert "Photosynthesis converts light" in provider.calls[0]["prompt"]


def test_generate_questions_dedupes_across_batches() -> None:
    duplicate = _mcq("What is the definition of photosynthesis?")
    provider = FakeProvider(
        [
            json.dumps({"questions": [duplicate, _open_q("Explain the Calvin cycle.")]}),
            json.dumps({"questions": [duplicate, _open_q("Describe respiration."), _open_q("Describe enzymes.")]}),
        ]
    )
    questions = generate_questions(
        provider=provider,
        chunks=CHUNKS,
        num_questions=3,
        question_types=["mcq", "short_answer"],
        difficulty="medium",
        topic=None,
    )
    assert len(questions) == 3
    texts = [q.text for q in questions]
    assert len(set(texts)) == 3


def test_generate_questions_stops_response_after_failure_but_keeps_collected() -> None:
    batch = [_mcq("Where does photosynthesis occur?")]
    provider = FakeProvider(
        responses=[json.dumps({"questions": batch})],
        fail_on=1,
        error=LLMConnectionError("ollama down", user_message="Ollama is not reachable."),
    )
    questions = generate_questions(
        provider=provider,
        chunks=CHUNKS,
        num_questions=4,
        question_types=["mcq"],
        difficulty="easy",
        topic=None,
    )
    # The first batch succeeded; the second failed. Keep collected questions.
    assert len(questions) == 1


def test_generate_questions_returns_fewer_when_context_is_small() -> None:
    provider = FakeProvider([json.dumps({"questions": [_mcq("What is the first stage of photosynthesis?")]})])
    questions = generate_questions(
        provider=provider,
        chunks=CHUNKS,
        num_questions=20,
        question_types=["mcq"],
        difficulty="hard",
        topic=None,
    )
    assert len(questions) == 1  # the model only produced one per call, no inventing


def test_generate_questions_raises_when_first_batch_fails() -> None:
    provider = FakeProvider(
        responses=[],
        fail_on=0,
        error=LLMConnectionError("ollama down", user_message="Ollama is not reachable."),
    )
    with pytest.raises(LLMConnectionError):
        generate_questions(
            provider=provider,
            chunks=CHUNKS,
            num_questions=4,
            question_types=["mcq"],
            difficulty="easy",
            topic=None,
        )