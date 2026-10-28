"""SQLAlchemy 2.0 ORM models for Quizora — RAG based study assistant.

All schema tables are defined here up front (Phase 1) so the database can be
created once and filled in by later phases:

- documents: uploaded files + ingestion status
- quizzes / questions: generated quiz structure
- attempts / attempt_answers: student submissions and per-question feedback
"""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import JSON, BigInteger, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Declarative base for all Quizora tables."""


class DocumentStatus(str, enum.Enum):
    """Lifecycle of an uploaded document."""

    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class QuizStatus(str, enum.Enum):
    """Lifecycle of a generated quiz."""

    GENERATING = "generating"
    READY = "ready"
    FAILED = "failed"


class QuestionType(str, enum.Enum):
    """Supported question types."""

    MCQ = "mcq"
    SHORT_ANSWER = "short_answer"
    LONG_ANSWER = "long_answer"


class Difficulty(str, enum.Enum):
    """Supported difficulty levels."""

    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class Document(Base):
    """An uploaded study document (PDF or PPTX)."""

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    original_filename: Mapped[str] = mapped_column(String(512))
    stored_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    content_type: Mapped[str] = mapped_column(String(256))
    file_size: Mapped[int] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(String(32), default=DocumentStatus.PROCESSING.value, index=True)
    source_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    num_chunks: Mapped[int | None] = mapped_column(Integer, nullable=True)
    embedding_model: Mapped[str | None] = mapped_column(String(256), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    quizzes: Mapped[list["Quiz"]] = relationship(back_populates="document", cascade="all, delete-orphan")


class Quiz(Base):
    """A generated quiz linked to one document."""

    __tablename__ = "quizzes"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    requested_num_questions: Mapped[int] = mapped_column(Integer)
    question_types: Mapped[list[str]] = mapped_column(JSON)
    difficulty: Mapped[str] = mapped_column(String(16))
    topic: Mapped[str | None] = mapped_column(String(512), nullable=True)
    mode: Mapped[str] = mapped_column(String(16), default="local")
    status: Mapped[str] = mapped_column(String(32), default=QuizStatus.GENERATING.value, index=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    document: Mapped[Document] = relationship(back_populates="quizzes")
    questions: Mapped[list["Question"]] = relationship(
        back_populates="quiz", cascade="all, delete-orphan", order_by="Question.position"
    )
    attempts: Mapped[list["Attempt"]] = relationship(back_populates="quiz", cascade="all, delete-orphan")


class Question(Base):
    """A single question inside a quiz."""

    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    quiz_id: Mapped[int] = mapped_column(ForeignKey("quizzes.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(Integer)
    type: Mapped[str] = mapped_column(String(32))
    difficulty: Mapped[str] = mapped_column(String(16))
    text: Mapped[str] = mapped_column(Text)
    options: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    correct_option: Mapped[int | None] = mapped_column(Integer, nullable=True)  # index into options (MCQ only)
    reference_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_points: Mapped[list[str]] = mapped_column(JSON, default=list)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_chunk_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    source_page_numbers: Mapped[list[int]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    quiz: Mapped[Quiz] = relationship(back_populates="questions")
    attempt_answers: Mapped[list["AttemptAnswer"]] = relationship(back_populates="question", cascade="all, delete-orphan")


class Attempt(Base):
    """One student submission of a quiz (evaluation run)."""

    __tablename__ = "attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    quiz_id: Mapped[int] = mapped_column(ForeignKey("quizzes.id", ondelete="CASCADE"), index=True)
    mode: Mapped[str] = mapped_column(String(16), default="local")
    total_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    quiz: Mapped[Quiz] = relationship(back_populates="attempts")
    answers: Mapped[list["AttemptAnswer"]] = relationship(
        back_populates="attempt", cascade="all, delete-orphan", order_by="AttemptAnswer.id"
    )


class AttemptAnswer(Base):
    """Per-question feedback produced by the evaluator for one attempt."""

    __tablename__ = "attempt_answers"

    id: Mapped[int] = mapped_column(primary_key=True)
    attempt_id: Mapped[int] = mapped_column(ForeignKey("attempts.id", ondelete="CASCADE"), index=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"), index=True)
    user_answer: Mapped[str] = mapped_column(Text)
    selected_option: Mapped[int | None] = mapped_column(Integer, nullable=True)  # MCQ-only choice index
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    verdict: Mapped[str | None] = mapped_column(String(32), nullable=True)
    covered_points: Mapped[list[str]] = mapped_column(JSON, default=list)
    missed_points: Mapped[list[str]] = mapped_column(JSON, default=list)
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    attempt: Mapped[Attempt] = relationship(back_populates="answers")
    question: Mapped[Question] = relationship(back_populates="attempt_answers")