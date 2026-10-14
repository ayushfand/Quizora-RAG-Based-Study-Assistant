"""Document upload / list / detail / delete endpoints."""

from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..models.entities import Document, DocumentStatus
from ..rag.vectorstore import VectorStore
from ..schemas.documents import DocumentRead
from ..services.document_processor import process_document

router = APIRouter(prefix="/documents", tags=["documents"])

ALLOWED_EXTENSIONS = {".pdf", ".pptx"}
_UPLOAD_CHUNK_BYTES = 1024 * 1024

_documents_dir = Path(__file__).resolve().parent.parent.parent / "data" / "documents"


def _resolve_document(document_id: int, db: Session) -> Document:
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found")
    return document


def sanitize_filename(filename: str) -> str:
    """Strip path components and unsafe characters from an uploaded file name."""
    name = Path(filename or "").name
    name = re.sub(r'[\x00-\x1f<>:"/\\|?*]', "_", name)
    name = name.strip().strip(".")
    if not name:
        name = "upload"
    return name[:200]


@router.post("", status_code=201, response_model=DocumentRead, summary="Upload a PDF or PPTX document")
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks(),
) -> DocumentRead:
    settings = get_settings()
    extension = Path(file.filename or "").suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{extension or '(none)'}'. Only {sorted(ALLOWED_EXTENSIONS)} are allowed.",
        )

    safe_name = sanitize_filename(file.filename or "upload")
    document = Document(
        original_filename=safe_name,
        content_type=file.content_type or "application/octet-stream",
        file_size=0,
        status=DocumentStatus.PROCESSING.value,
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    _documents_dir.mkdir(parents=True, exist_ok=True)
    destination = _documents_dir / f"{document.id}{extension}"
    size = 0
    try:
        with destination.open("wb") as out:
            while chunk := await file.read(_UPLOAD_CHUNK_BYTES):
                size += len(chunk)
                if size > settings.max_upload_mb * 1024 * 1024:
                    raise HTTPException(
                        status_code=413,
                        detail=f"File exceeds the {settings.max_upload_mb} MB upload limit.",
                    )
                out.write(chunk)
    except HTTPException:
        destination.unlink(missing_ok=True)
        db.delete(document)
        db.commit()
        raise
    except Exception:
        destination.unlink(missing_ok=True)
        db.delete(document)
        db.commit()
        raise

    if size == 0:
        destination.unlink(missing_ok=True)
        db.delete(document)
        db.commit()
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")

    document.stored_path = str(destination)
    document.file_size = size
    db.commit()
    db.refresh(document)

    background_tasks.add_task(process_document, document.id)
    return DocumentRead.model_validate(document)


@router.get("", response_model=list[DocumentRead], summary="List uploaded documents")
def list_documents(db: Session = Depends(get_db)) -> list[DocumentRead]:
    documents = db.scalars(select(Document).order_by(Document.created_at.desc())).all()
    return [DocumentRead.model_validate(doc) for doc in documents]


@router.get("/{document_id}", response_model=DocumentRead, summary="Get one document")
def get_document(document_id: int, db: Session = Depends(get_db)) -> DocumentRead:
    return DocumentRead.model_validate(_resolve_document(document_id, db))


@router.delete("/{document_id}", status_code=204, summary="Delete a document and its index")
def delete_document(document_id: int, db: Session = Depends(get_db)):
    document = _resolve_document(document_id, db)
    # Remove the vector index first (best-effort), then file + DB row.
    settings = get_settings()
    try:
        vectorstore = VectorStore(persistent_dir=settings.chroma_dir, embedding_model="")
        vectorstore.delete_collection(document_id)
    except Exception:
        pass  # index deletion must not block removing the document
    if document.stored_path:
        Path(document.stored_path).unlink(missing_ok=True)
    db.delete(document)
    db.commit()