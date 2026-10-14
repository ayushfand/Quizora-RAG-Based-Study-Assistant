"""Background document ingestion: parse → chunk → embed → store.

Runs as a FastAPI BackgroundTask after each upload. It opens its own DB
session so it is independent of the request lifecycle, and it marks the
document ``ready`` or ``failed`` with a human-readable error message.
"""

from __future__ import annotations

from pathlib import Path

from ..config import get_settings
from ..db import SessionLocal
from ..llm.errors import LLMError
from ..models.entities import Document, DocumentStatus
from ..rag.chunking import Chunk, chunk_pages
from ..rag.embeddings import OllamaEmbeddingProvider
from ..rag.parsers import parse_document
from ..rag.vectorstore import EmbeddingModelMismatchError, VectorStore


def process_document(document_id: int) -> None:
    """Ingest one uploaded document (parse, chunk, embed, store)."""
    db = SessionLocal()
    try:
        document = db.get(Document, document_id)
        if document is None or not document.stored_path:
            return
        try:
            _ingest(document)
            document.status = DocumentStatus.READY.value
            db.commit()
        except (LLMError, EmbeddingModelMismatchError, ValueError, RuntimeError) as exc:
            # ImportError is caught via RuntimeError. LLMError has a friendly
            # user-facing message; others are truncated for the UI.
            message = getattr(exc, "user_message", None) or str(exc)
            document.status = DocumentStatus.FAILED.value
            document.error_message = message[:2000]
            db.commit()
        except Exception as exc:  # noqa: BLE001 - ingestion must never crash the worker
            document.status = DocumentStatus.FAILED.value
            document.error_message = f"Unexpected ingestion error: {str(exc)[:2000]}"
            db.commit()
    finally:
        db.close()


def _ingest(document: Document) -> None:
    settings = get_settings()
    source_type = Path(document.stored_path).suffix.lower().lstrip(".")
    pages = parse_document(document.stored_path, source_type)
    chunks: list[Chunk] = chunk_pages(pages, source_name=document.original_filename)

    embedder = OllamaEmbeddingProvider(
        base_url=settings.ollama_base_url,
        model=settings.ollama_embed_model,
        timeout_seconds=settings.llm_timeout_seconds,
    )
    embeddings = embedder.embed([chunk.text for chunk in chunks])

    vectorstore = VectorStore(
        persistent_dir=settings.chroma_dir,
        embedding_model=embedder.name,
    )
    vectorstore.add_chunks(document_id=document.id, chunks=chunks, embeddings=embeddings)

    document.source_type = source_type
    document.num_chunks = len(chunks)
    document.embedding_model = embedder.name
    document.error_message = None