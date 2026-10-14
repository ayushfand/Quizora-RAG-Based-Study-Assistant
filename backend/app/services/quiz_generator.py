"""Quiz generation: retrieve context → batch-call the LLM → persist questions.

Generation runs as a background task so local (Ollama) generation can take a
minute without blocking the API. Retrieval is topic-aware; without a topic the
chunks are sampled evenly so questions cover the whole document.
"""

from __future__ import annotations

import math
import re

from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import SessionLocal
from ..llm.base import LLMProvider
from ..llm.errors import LLMConfigurationError, LLMError
from ..models.entities import Document, Quiz, Question, QuizStatus
from ..prompts.quiz_generation import QUIZ_SYSTEM_PROMPT, build_batch_prompt
from ..rag.embeddings import OllamaEmbeddingProvider
from ..rag.retriever import Retriever
from ..rag.vectorstore import StoredChunk, VectorStore
from ..schemas.generated import QuestionBatch, GeneratedQuestion
from ..schemas.quizzes import QuizGenerateRequest

BATCH_SIZE = 4
DEFAULT_MAX_CONTEXT_CHUNKS = 24
MAX_QUESTIONS_PER_GENERATION = 20


def create_quiz_and_schedule(db: Session, request: QuizGenerateRequest) -> Quiz:
    """Create a ``generating`` quiz row ready for the background task.

    Raises ValueError with a user-facing message on invalid input.
    """
    request.validate_types()
    document = db.get(Document, request.document_id)
    if document is None:
        raise ValueError(f"Document {request.document_id} not found")
    if document.status != "ready":
        raise ValueError(
            f"Document '{document.original_filename}' is not ready yet "
            f"(status: {document.status}). Wait for ingestion to finish."
        )
    quiz = Quiz(
        document_id=document.id,
        requested_num_questions=request.num_questions,
        question_types=request.normalized_question_types(),
        difficulty=request.difficulty,
        topic=request.topic,
        mode=request.mode or get_settings().default_llm_mode,
        status=QuizStatus.GENERATING.value,
    )
    db.add(quiz)
    db.commit()
    db.refresh(quiz)
    return quiz


def generate_quiz_background(quiz_id: int) -> None:
    """Run quiz generation for one quiz row; update its status when done."""
    db = SessionLocal()
    try:
        quiz = db.get(Quiz, quiz_id)
        if quiz is None:
            return
        try:
            questions = _generate_for_quiz(db, quiz)
            for position, question in enumerate(questions, start=1):
                db.add(_persist_question(quiz.id, position, question, quiz))
            quiz.status = QuizStatus.READY.value
            quiz.error_message = None
            db.commit()
        except (LLMError, ValueError, RuntimeError) as exc:
            quiz.status = QuizStatus.FAILED.value
            quiz.error_message = (getattr(exc, "user_message", None) or str(exc))[:2000]
            db.commit()
        except Exception as exc:  # noqa: BLE001 - generation must never crash the worker
            quiz.status = QuizStatus.FAILED.value
            quiz.error_message = f"Unexpected generation error: {str(exc)[:2000]}"
            db.commit()
    finally:
        db.close()


def _generate_for_quiz(db: Session, quiz: Quiz) -> list[GeneratedQuestion]:
    settings = get_settings()
    document = db.get(Document, quiz.document_id)
    if document is None:
        raise ValueError(f"Document for quiz {quiz.id} no longer exists")

    chunks = _retrieve_context(document, quiz.topic)
    if not chunks:
        raise LLMError(
            "No indexed chunks were found for this document.",
            user_message="The document has no indexed content. Re-upload it.",
        )
    # Grounding cap: never request more questions than the context can support.
    max_supported = min(MAX_QUESTIONS_PER_GENERATION, quiz.requested_num_questions, len(chunks) * 2)
    provider = _provider_for_mode(quiz.mode)
    questions = generate_questions(
        provider=provider,
        chunks=chunks,
        num_questions=max_supported,
        question_types=quiz.question_types,
        difficulty=quiz.difficulty,
        topic=quiz.topic,
        context_for=quiz,
    )
    if not questions:
        raise LLMError(
            "The LLM could not generate any valid questions from the source material.",
            user_message="No valid questions could be generated. Try a different topic or difficulty.",
        )
    return questions


def _retrieve_context(document: Document, topic: str | None) -> list[StoredChunk]:
    """Return source chunks: semantic search for a topic, even sampling otherwise."""
    settings = get_settings()
    expected_model = document.embedding_model
    current_model = f"ollama/{settings.ollama_embed_model}"
    if expected_model and expected_model != current_model:
        raise LLMConfigurationError(
            f"Document was indexed with embedding model '{expected_model}' but the system "
            f"now uses '{current_model}'.",
            user_message=(
                "This document was indexed with a different embedding model. "
                "Restore OLLAMA_EMBED_MODEL to the model used when it was uploaded, "
                "or delete and re-upload the document."
            ),
        )
    embedder = OllamaEmbeddingProvider(
        base_url=settings.ollama_base_url,
        model=settings.ollama_embed_model,
        timeout_seconds=settings.llm_timeout_seconds,
    )
    vectorstore = VectorStore(persistent_dir=settings.chroma_dir, embedding_model=embedder.name)
    retriever = Retriever(vectorstore=vectorstore, embedder=embedder)
    topic_for_search = (topic or "").strip() or None
    return retriever.retrieve(document.id, topic_for_search, max_chunks=DEFAULT_MAX_CONTEXT_CHUNKS)


def _provider_for_mode(mode: str) -> LLMProvider:
    from ..llm.factory import get_provider

    return get_provider(mode)


def generate_questions(
    provider: LLMProvider,
    chunks: list[StoredChunk],
    num_questions: int,
    question_types: list[str],
    difficulty: str,
    topic: str | None,
    context_for: Quiz | None = None,
) -> list[GeneratedQuestion]:
    """Generate and de-duplicate questions from source chunks, in small batches.

    Batches of at most :data:`BATCH_SIZE` questions keep the small local model
    reliable. Returns fewer than ``num_questions`` when the source material or
    the model cannot produce more — facts are never invented. When ``context_for``
    is given, the batch context is attached to it so persistence can record
    source chunk ids.
    """
    if context_for is not None:
        context_for._generation_context = list(chunks)  # type: ignore[attr-defined]

    max_batches = math.ceil(num_questions / BATCH_SIZE) + 1
    collected: list[GeneratedQuestion] = []
    seen: set[str] = set()

    for _ in range(max_batches):
        remaining = num_questions - len(collected)
        if remaining <= 0:
            break
        batch_size = min(BATCH_SIZE, remaining)
        prompt = build_batch_prompt(chunks, batch_size, question_types, difficulty, topic)
        try:
            batch = provider.generate_json(prompt, QuestionBatch, system=QUIZ_SYSTEM_PROMPT).questions
        except LLMError:
            if collected:
                break  # keep the questions already generated for this quiz
            raise
        added = 0
        for question in batch:
            key = _normalize(question.text)
            if key in seen:
                continue
            seen.add(key)
            collected.append(question)
            added += 1
            if len(collected) >= num_questions:
                break
        if added == 0:
            break  # avoid spinning when the model only repeats itself

    return collected


def _normalize(text: str) -> str:
    """Normalize question text for (near-)duplicate detection."""
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _persist_question(quiz_id: int, position: int, question: GeneratedQuestion, quiz: Quiz) -> Question:
    context: list[StoredChunk] = getattr(quiz, "_generation_context", []) or []
    source_ids = [hit.chunk_id for hit in context]
    pages = sorted({hit.page_number for hit in context})
    return Question(
        quiz_id=quiz_id,
        position=position,
        type=question.type,
        difficulty=question.difficulty,
        text=question.text,
        options=question.options,
        correct_option=question.correct_option if question.type == "mcq" else None,
        reference_answer=question.reference_answer or question.explanation,
        key_points=question.key_points or [],
        explanation=question.explanation,
        source_chunk_ids=source_ids,
        source_page_numbers=pages,
    )