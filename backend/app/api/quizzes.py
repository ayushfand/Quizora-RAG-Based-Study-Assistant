"""Quiz endpoints: generate, fetch, list."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..db import get_db
from ..models.entities import Quiz
from ..schemas.quizzes import QuizCreateResponse, QuizGenerateRequest, QuizRead
from ..services.quiz_generator import create_quiz_and_schedule, generate_quiz_background

router = APIRouter(prefix="/quizzes", tags=["quizzes"])


@router.post(
    "/generate",
    response_model=QuizCreateResponse,
    status_code=202,
    summary="Generate a quiz from a document (runs in the background)",
)
def generate_quiz(
    request: QuizGenerateRequest,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db),
) -> QuizCreateResponse:
    """Validate input, create a ``generating`` quiz, and schedule generation."""
    try:
        quiz = create_quiz_and_schedule(db, request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    background_tasks.add_task(generate_quiz_background, quiz.id)
    return QuizCreateResponse(id=quiz.id, status=quiz.status)


@router.get("", response_model=list[QuizRead], summary="List quizzes (optionally for one document)")
def list_quizzes(
    document_id: int | None = None,
    db: Session = Depends(get_db),
) -> list[QuizRead]:
    statement = select(Quiz).options(selectinload(Quiz.questions)).order_by(Quiz.created_at.desc())
    if document_id is not None:
        statement = statement.where(Quiz.document_id == document_id)
    quizzes = db.scalars(statement).all()
    return [QuizRead.model_validate(quiz) for quiz in quizzes]


@router.get("/{quiz_id}", response_model=QuizRead, summary="Get a quiz with its questions")
def get_quiz(quiz_id: int, db: Session = Depends(get_db)) -> QuizRead:
    quiz = db.get(Quiz, quiz_id, options=[selectinload(Quiz.questions)])
    if quiz is None:
        raise HTTPException(status_code=404, detail=f"Quiz {quiz_id} not found")
    return QuizRead.model_validate(quiz)


@router.delete("/{quiz_id}", status_code=204, summary="Delete a quiz and its questions/attempts")
def delete_quiz(quiz_id: int, db: Session = Depends(get_db)):
    quiz = db.get(Quiz, quiz_id)
    if quiz is None:
        raise HTTPException(status_code=404, detail=f"Quiz {quiz_id} not found")
    db.delete(quiz)
    db.commit()