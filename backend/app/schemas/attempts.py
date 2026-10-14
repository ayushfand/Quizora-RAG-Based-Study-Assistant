"""Pydantic DTOs for quiz attempts and evaluation feedback."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SubmittedAnswer(BaseModel):
    """One answer in a submission (MCQ choice, free text, or both)."""

    question_id: int
    selected_option: int | None = Field(default=None, ge=0, le=3)
    answer_text: str | None = Field(default=None, max_length=8000)


class AttemptCreate(BaseModel):
    """Payload for POST /api/attempts."""

    quiz_id: int
    mode: Literal["local", "gemini"] | None = None
    answers: list[SubmittedAnswer] = Field(default_factory=list)


class AnswerFeedback(BaseModel):
    """Evaluation result for a single question inside an attempt."""

    question_id: int
    position: int
    type: str
    text: str
    options: list[str] | None
    correct_option: int | None
    selected_option: int | None
    user_answer: str
    score: float
    max_score: float
    verdict: str
    covered_points: list[str]
    missed_points: list[str]
    feedback: str
    model_answer: str | None
    source_page_numbers: list[int]


class AttemptRead(BaseModel):
    """A full attempt with per-question feedback."""

    id: int
    quiz_id: int
    mode: str
    total_score: float
    max_score: float
    created_at: datetime
    answers: list[AnswerFeedback] = Field(default_factory=list)


class AttemptSummary(BaseModel):
    """Compact attempt row for history lists."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    quiz_id: int
    mode: str
    total_score: float | None
    max_score: float | None
    created_at: datetime
