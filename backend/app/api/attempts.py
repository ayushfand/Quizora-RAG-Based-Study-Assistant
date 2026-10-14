"""Attempt endpoints: submit a quiz for evaluation, list history, fetch results."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..db import get_db
from ..llm.errors import LLMError
from ..llm.factory import get_provider
from ..models.entities import Attempt, AttemptAnswer
from ..schemas.attempts import AnswerFeedback, AttemptCreate, AttemptRead, AttemptSummary
from ..services.evaluator import create_attempt

router = APIRouter(prefix="/attempts", tags=["attempts"])


def _load_attempt(db: Session, attempt_id: int) -> Attempt:
    attempt = db.get(
        Attempt,
        attempt_id,
        options=[selectinload(Attempt.answers).selectinload(AttemptAnswer.question)],
    )
    if attempt is None:
        raise HTTPException(status_code=404, detail=f"Attempt {attempt_id} not found")
    return attempt


def _to_read(attempt: Attempt) -> AttemptRead:
    answers = [
        AnswerFeedback(
            question_id=answer.question_id,
            position=answer.question.position,
            type=answer.question.type,
            text=answer.question.text,
            options=answer.question.options,
            correct_option=answer.question.correct_option,
            selected_option=answer.selected_option,
            user_answer=answer.user_answer,
            score=answer.score or 0.0,
            max_score=answer.max_score if answer.max_score is not None else 10.0,
            verdict=answer.verdict or "",
            covered_points=list(answer.covered_points or []),
            missed_points=list(answer.missed_points or []),
            feedback=answer.feedback or "",
            model_answer=answer.model_answer,
            source_page_numbers=list(answer.question.source_page_numbers or []),
        )
        for answer in attempt.answers
        if answer.question is not None
    ]
    return AttemptRead(
        id=attempt.id,
        quiz_id=attempt.quiz_id,
        mode=attempt.mode,
        total_score=attempt.total_score or 0.0,
        max_score=attempt.max_score or 0.0,
        created_at=attempt.created_at,
        answers=answers,
    )


@router.post("", response_model=AttemptRead, status_code=201, summary="Submit answers for AI evaluation")
def submit_attempt(request: AttemptCreate, db: Session = Depends(get_db)) -> AttemptRead:
    """Grade every question and persist the attempt with per-question feedback."""
    try:
        provider = get_provider(request.mode)
    except LLMError as exc:  # bad mode / missing key/config
        raise HTTPException(status_code=400, detail=exc.user_message) from exc

    try:
        attempt = create_attempt(db, request, provider)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LLMError as exc:  # provider unreachable / bad structured output
        raise HTTPException(status_code=503, detail=exc.user_message) from exc

    return _to_read(_load_attempt(db, attempt.id))


@router.get("", response_model=list[AttemptSummary], summary="List attempts (optionally for one quiz)")
def list_attempts(
    quiz_id: int | None = None,
    db: Session = Depends(get_db),
) -> list[AttemptSummary]:
    statement = select(Attempt).order_by(Attempt.created_at.desc(), Attempt.id.desc())
    if quiz_id is not None:
        statement = statement.where(Attempt.quiz_id == quiz_id)
    attempts = db.scalars(statement).all()
    return [AttemptSummary.model_validate(attempt) for attempt in attempts]


@router.get("/{attempt_id}", response_model=AttemptRead, summary="Get an attempt with its feedback")
def get_attempt(attempt_id: int, db: Session = Depends(get_db)) -> AttemptRead:
    return _to_read(_load_attempt(db, attempt_id))


@router.delete("/{attempt_id}", status_code=204, summary="Delete an attempt")
def delete_attempt(attempt_id: int, db: Session = Depends(get_db)):
    attempt = db.get(Attempt, attempt_id)
    if attempt is None:
        raise HTTPException(status_code=404, detail=f"Attempt {attempt_id} not found")
    db.delete(attempt)
    db.commit()
