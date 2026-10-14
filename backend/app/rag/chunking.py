"""Text chunking for the RAG pipeline.

Chunks are built per page/slide (so a chunk never bleeds across pages, keeping
the page-number metadata accurate) and carry a global chunk index. Chunking is
sentence-aware: it groups sentences until the target size is reached and keeps
an overlap tail so context is preserved across boundaries.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .parsers import PageContent

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?。！？])\s+")
_DEFAULT_CHUNK_SIZE = 800
_DEFAULT_OVERLAP = 120


@dataclass(frozen=True)
class Chunk:
    """A retrievable text chunk with provenance metadata."""

    text: str
    page_number: int
    chunk_index: int  # global index across the whole document
    source_name: str = ""


def chunk_text(
    text: str,
    chunk_size: int = _DEFAULT_CHUNK_SIZE,
    overlap: int = _DEFAULT_OVERLAP,
) -> list[str]:
    """Split a single text blob into overlapping chunks of ~``chunk_size`` chars.

    Args:
        text: raw text (already de-duplicated/whitespace-normalized).
        chunk_size: target maximum length of a chunk in characters.
        overlap: how many characters of the previous chunk to carry over.

    Returns:
        A list of chunk strings. Empty text yields an empty list.
    """
    normalized = " ".join(text.split())
    if not normalized:
        return []

    sentences = [s for s in _SENTENCE_SPLIT.split(normalized) if s.strip()]
    if not sentences:
        return [normalized[:chunk_size]]

    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    def flush() -> None:
        nonlocal current, current_len
        if current:
            chunks.append(" ".join(current))
            # Keep an overlap tail from the chunk we just flushed.
            tail: list[str] = []
            tail_len = 0
            for sentence in reversed(current):
                if tail_len + len(sentence) > overlap and tail:
                    break
                tail.insert(0, sentence)
                tail_len += len(sentence) + 1
            current = tail
            current_len = tail_len

    for sentence in sentences:
        if current_len + len(sentence) + 1 > chunk_size and current:
            flush()
        if len(sentence) > chunk_size:
            # Rare: a single sentence longer than the target — hard-split it.
            flush()
            current = []
            current_len = 0
            words = sentence.split()
            piece: list[str] = []
            piece_len = 0
            for word in words:
                if piece_len + len(word) + 1 > chunk_size and piece:
                    chunks.append(" ".join(piece))
                    piece = piece[max(0, len(piece) - max(1, overlap // 8)) :]
                    piece_len = sum(len(w) + 1 for w in piece)
                piece.append(word)
                piece_len += len(word) + 1
            if piece:
                chunks.append(" ".join(piece))
            continue
        current.append(sentence)
        current_len += len(sentence) + 1

    flush()
    return [c for c in chunks if c]


def chunk_pages(
    pages: list[PageContent],
    source_name: str,
    chunk_size: int = _DEFAULT_CHUNK_SIZE,
    overlap: int = _DEFAULT_OVERLAP,
) -> list[Chunk]:
    """Chunk per-page text and attach provenance metadata to each chunk.

    Args:
        pages: parsed pages/slides (text + 1-based number).
        source_name: original file name, stored on every chunk.
        chunk_size/overlap: forwarded to :func:`chunk_text`.

    Returns:
        Chunks ordered by page then by position within the page.
    """
    chunks: list[Chunk] = []
    index = 0
    for page in pages:
        for piece in chunk_text(page.text, chunk_size=chunk_size, overlap=overlap):
            chunks.append(
                Chunk(
                    text=piece,
                    page_number=page.page_number,
                    chunk_index=index,
                    source_name=source_name,
                )
            )
            index += 1
    return chunks