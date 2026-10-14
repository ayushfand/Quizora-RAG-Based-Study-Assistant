"""Pydantic DTOs for quizzes."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

QuestionTypeValue = Literal["mcq", "short_answer", "long_answer"]
DifficultyValue = Literal["easy", "medium", "hard"]
ValidQuestionTypes = ("mcq", "short_answer", "long_answer")


class QuizGenerateRequest(BaseModel):
    """Payload for POST /api/quizzes/generate."""

    document_id: int
    num_questions: int = Field(5, ge=1, le=20)
    question_types: list[str] = Field(default_factory=lambda: ["mcq", "short_answer", "long_answer"])
    difficulty: DifficultyValue = "medium"
    topic: str | None = Field(default=None, max_length=500)
    mode: Literal["local", "gemini"] | None = None

    def normalized_question_types(self) -> list[str]:
        """Validate and return a de-duplicated, ordered type list."""
        by_value: dict[str, str] = {}
        for item in self.question_types:
            value = item.strip().lower()
            if value not in ValidQuestionTypes:
                raise ValueError(
                    f"Invalid question type '{item}'. Supported: {', '.join(ValidQuestionTypes)}."
                )
            by_value[value] = value
        return list(by_value.values())

    def validate_types(self) -> None:
        """Raise ValueError on unsupported question types (used by the API)."""
        self.normalized_question_types()


class QuizCreateResponse(BaseModel):
    """Immediate response after requesting generation."""

    id: int
    status: str


class QuestionRead(BaseModel):
    """A question exposed to the student (answers are withheld here)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    position: int
    type: str
    difficulty: str
    text: str
    options: list[str] | None
    source_page_numbers: list[int]


class QuizRead(BaseModel):
    """A quiz with its questions (without answers)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    requested_num_questions: int
    question_types: list[str]
    difficulty: str
    topic: str | None
    mode: str
    status: str
    error_message: str | None
    created_at: datetime
    questions: list[QuestionRead] = Field(default_factory=list)