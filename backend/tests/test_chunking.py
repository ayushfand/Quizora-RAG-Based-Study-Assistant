"""Tests for the sentence-aware text chunker."""

from __future__ import annotations

from app.rag.chunking import Chunk, chunk_pages, chunk_text
from app.rag.parsers import PageContent

SAMPLE = (
    "Photosynthesis is the process by which plants convert light into chemical energy. "
    "It takes place in the chloroplasts. "
    "The light-dependent reactions occur in the thylakoid membrane. "
    "The Calvin cycle fixes carbon dioxide into glucose. "
    "Water is split to release oxygen during the light reactions. "
    "Enzymes catalyze each step of the pathway."
)


def _words(text: str) -> set[str]:
    return set(text.lower().replace(".", "").split())


def test_chunk_text_produces_bounded_chunks() -> None:
    chunks = chunk_text(SAMPLE, chunk_size=120, overlap=20)
    assert len(chunks) >= 2
    for chunk in chunks:
        assert len(chunk) <= 220  # chunk_size + small tolerance


def test_chunk_text_preserves_all_words() -> None:
    chunks = chunk_text(SAMPLE, chunk_size=120, overlap=20)
    reconstructed = " ".join(chunks)
    assert _words(reconstructed) == _words(SAMPLE)


def test_chunk_text_single_short_passage_is_one_chunk() -> None:
    chunks = chunk_text("Short passage with a couple sentences. It fits.", chunk_size=500)
    assert len(chunks) == 1
    assert "couple sentences" in chunks[0]


def test_chunk_text_empty_input() -> None:
    assert chunk_text("   \n  ") == []


def test_chunk_pages_keeps_page_numbers() -> None:
    pages = [
        PageContent(text="First page content. More sentences here. And more.", page_number=1),
        PageContent(text="Second page content. With a few sentences too.", page_number=2),
    ]
    chunks = chunk_pages(pages, source_name="notes.pdf", chunk_size=200, overlap=20)
    assert chunks
    assert all(isinstance(c, Chunk) for c in chunks)
    assert {c.page_number for c in chunks} == {1, 2}
    assert all(c.source_name == "notes.pdf" for c in chunks)
    # Global indices are sequential.
    indices = [c.chunk_index for c in chunks]
    assert indices == list(range(len(chunks)))