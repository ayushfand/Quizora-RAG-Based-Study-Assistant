"""Evaluation service: grade a submitted quiz attempt.

- MCQ answers are graded deterministically (:mod:`app.services.mcq`); the
  explanation stored with the question is reused as feedback — no LLM call.
- Short/long answers use an LLM-as-judge with the rubric captured at generation
  time (reference answer + key points) plus the source chunks the question came
  from.
- Blank answers always score 0 and never reach the LLM.

The service is provider-injected so it can be unit-tested with a fake LLM.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.orm import Session, selectinload

from ..llm.base import LLMProvider
from ..models.entities import Attempt, AttemptAnswer, Document, Question, Quiz, QuizStatus
from ..prompts.evaluation import EVALUATION_SYSTEM_PROMPT, build_evaluation_prompt
from ..schemas.attempts import AttemptCreate, SubmittedAnswer
from ..schemas.generated import AnswerEvaluation
from .mcq import grade_mcq

MAX_QUESTION_SCORE = 10.0

# Verdict labels (stable, safe to render directly in the UI).
VERDICT_CORRECT = "correct"
VERDICT_PARTIAL = "partial"
VERDICT_INCORRECT = "incorrect"
VERDICT_BLANK = "blank"


@dataclass
class EvaluationResult:
    """Normalized evaluation for a single question (0–10 scale)."""

    score: float
    max_score: float = MAX_QUESTION_SCORE
    verdict: str = VERDICT_INCORRECT
    covered_points: list[str] = field(default_factory=list)
    missed_points: list[str] = field(default_factory=list)
    feedback: str = ""
    model_answer: str | None = None


def create_attempt(db: Session, request: AttemptCreate, provider: LLMProvider) -> Attempt:
    """Grade a submission, persist the attempt, and return it with feedback.

    Raises :class:`ValueError` with a user-facing message on invalid input.
    """
    quiz = db.get(
        Quiz,
        request.quiz_id,
        options=[selectinload(Quiz.questions), selectinload(Quiz.document)],
    )
    if quiz is None:
        raise ValueError(f"Quiz {request.quiz_id} not found")
    if quiz.status != QuizStatus.READY.value:
        raise ValueError(f"Quiz {quiz.id} is not ready yet (status: {quiz.status})")

    questions = list(quiz.questions)
    if not questions:
        raise ValueError(f"Quiz {quiz.id} has no questions to grade")

    submitted_by_id = _submitted_by_question(request, {q.id for q in questions})
    chunk_texts = load_document_chunk_texts(quiz.document)

    attempt = Attempt(quiz_id=quiz.id, mode=request.mode or quiz.mode or "local")
    db.add(attempt)
    db.flush()  # assign attempt.id before the answers reference it

    total = 0.0
    for question in questions:
        submitted = submitted_by_id.get(question.id)
        result = evaluate_answer(provider, question, submitted, chunk_texts)
        total += result.score
        attempt.answers.append(
            AttemptAnswer(
                question=question,
                user_answer=_user_answer_text(question, submitted),
                selected_option=submitted.selected_option if submitted else None,
                score=result.score,
                max_score=result.max_score,
                verdict=result.verdict,
                covered_points=result.covered_points,
                missed_points=result.missed_points,
                feedback=result.feedback,
                model_answer=result.model_answer,
            )
        )

    attempt.total_score = round(total, 2)
    attempt.max_score = round(MAX_QUESTION_SCORE * len(questions), 2)
    db.commit()
    db.refresh(attempt)
    return attempt


# --------------------------------------------------------------------- graders


def evaluate_answer(
    provider: LLMProvider,
    question: Question,
    submitted: SubmittedAnswer | None,
    chunk_texts: dict[str, str] | None = None,
) -> EvaluationResult:
    """Evaluate one submitted answer against one question."""
    if question.type == "mcq":
        return _evaluate_mcq(question, submitted)
    return _evaluate_open(provider, question, submitted, chunk_texts or {})


def _evaluate_mcq(question: Question, submitted: SubmittedAnswer | None) -> EvaluationResult:
    options = question.options or []
    correct_index = question.correct_option
    selected = submitted.selected_option if submitted is not None else None
    grade = grade_mcq(correct_index, selected)
    correct_text = _option_text(options, correct_index)
    explanation = (question.explanation or "").strip()

    if selected is None:
        feedback = "No answer was provided."
        if correct_text:
            feedback += f" The correct answer is: {correct_text}."
        if explanation:
            feedback += f" {explanation}"
        return EvaluationResult(
            score=0.0,
            verdict=VERDICT_BLANK,
            missed_points=[correct_text] if correct_text else [],
            feedback=feedback,
            model_answer=correct_text,
        )

    if grade.correct:
        return EvaluationResult(
            score=MAX_QUESTION_SCORE,
            verdict=VERDICT_CORRECT,
            covered_points=[correct_text] if correct_text else [],
            feedback=(question.explanation or "").strip() or "Correct — well done.",
            model_answer=correct_text,
        )

    feedback = f"The correct answer is: {correct_text}." if correct_text else "That choice was incorrect."
    if question.explanation:
        feedback += f" {question.explanation.strip()}"
    return EvaluationResult(
        score=0.0,
        verdict=VERDICT_INCORRECT,
        missed_points=[correct_text] if correct_text else [],
        feedback=feedback,
        model_answer=correct_text,
    )


def _evaluate_open(
    provider: LLMProvider,
    question: Question,
    submitted: SubmittedAnswer | None,
    chunk_texts: dict[str, str],
) -> EvaluationResult:
    answer = (submitted.answer_text or "").strip() if submitted else ""
    if not answer:
        feedback = (
            "No answer was provided. Compare what you know with the model answer "
            "and the key points that were expected."
        )
        return EvaluationResult(
            score=0.0,
            verdict=VERDICT_BLANK,
            missed_points=list(question.key_points or []),
            feedback=feedback,
            model_answer=question.reference_answer,
        )

    prompt = build_evaluation_prompt(
        question_text=question.text,
        question_type=question.type,
        difficulty=question.difficulty,
        reference_answer=question.reference_answer,
        key_points=list(question.key_points or []),
        source_chunks=_source_chunks_for(question, chunk_texts),
        student_answer=answer,
    )
    evaluation: AnswerEvaluation = provider.generate_json(  # type: ignore[assignment]
        prompt, AnswerEvaluation, system=EVALUATION_SYSTEM_PROMPT
    )

    score = max(0.0, min(MAX_QUESTION_SCORE, float(evaluation.score)))
    return EvaluationResult(
        score=score,
        verdict=_verdict_for_score(score),
        covered_points=list(evaluation.covered_points),
        missed_points=list(evaluation.missed_points),
        feedback=evaluation.feedback.strip(),
        model_answer=(evaluation.model_answer or question.reference_answer),
    )


def _verdict_for_score(score: float) -> str:
    if score >= 8.0:
        return VERDICT_CORRECT
    if score >= 5.0:
        return VERDICT_PARTIAL
    return VERDICT_INCORRECT


def _source_chunks_for(question: Question, chunk_texts: dict[str, str]) -> list[str]:
    return [chunk_texts[cid] for cid in (question.source_chunk_ids or []) if cid in chunk_texts]


def _option_text(options: list[str], index: int | None) -> str:
    """Return the text of the option at ``index`` (empty when out of range)."""
    if index is None:
        return ""
    if 0 <= index < len(options):
        return options[index]
    return ""


def _selected_option_text(question: Question, submitted: SubmittedAnswer | None) -> str:
    if submitted is None:
        return ""
    return _option_text(question.options or [], submitted.selected_option)


def _user_answer_text(question: Question, submitted: SubmittedAnswer | None) -> str:
    if question.type == "mcq":
        return _selected_option_text(question, submitted)
    return (submitted.answer_text or "").strip() if submitted else ""


def _submitted_by_question(request: AttemptCreate, quiz_question_ids: set[int]) -> dict[int, SubmittedAnswer]:
    by_id: dict[int, SubmittedAnswer] = {}
    for answer in request.answers:
        if answer.question_id in by_id:
            raise ValueError(f"Question {answer.question_id} was answered more than once")
        by_id[answer.question_id] = answer
    unknown = set(by_id) - quiz_question_ids
    if unknown:
        listed = ", ".join(str(qid) for qid in sorted(unknown))
        raise ValueError(f"Answers reference questions that are not part of this quiz: {listed}")
    return by_id


def load_document_chunk_texts(document: Document | None) -> dict[str, str]:
    """Return ``{chunk_id: text}`` for a document (empty when unavailable)."""
    if document is None:
        return {}
    try:
        from ..config import get_settings
        from ..rag.vectorstore import VectorStore

        settings = get_settings()
        store = VectorStore(
            persistent_dir=settings.chroma_dir,
            embedding_model=document.embedding_model or "",
        )
        return {hit.chunk_id: hit.text for hit in store.all_chunks(document.id)}
    except Exception:  # noqa: BLE001 - evaluation must work without the vector index
        return {}
