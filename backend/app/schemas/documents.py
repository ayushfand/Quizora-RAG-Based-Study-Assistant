"""Pydantic DTOs for documents."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentRead(BaseModel):
    """Document as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    original_filename: str
    content_type: str
    file_size: int
    status: str
    source_type: str | None
    num_chunks: int | None
    embedding_model: str | None
    error_message: str | None
    created_at: datetime