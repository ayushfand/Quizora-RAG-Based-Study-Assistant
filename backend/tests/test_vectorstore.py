"""Integration tests for the ChromaDB-backed vector store.

Embeddings are supplied directly (no Ollama), so these tests exercise the real
ChromaDB client deterministically.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.rag.chunking import Chunk
from app.rag.vectorstore import EmbeddingModelMismatchError, VectorStore

EMBED_MODEL = "test-embed"


def _chunk(text: str, page: int, index: int) -> Chunk:
    return Chunk(text=text, page_number=page, chunk_index=index, source_name="notes.pdf")


@pytest.fixture()
def store(tmp_path: Path) -> VectorStore:
    pytest.importorskip("chromadb")
    return VectorStore(persistent_dir=str(tmp_path / "chroma"), embedding_model=EMBED_MODEL)


def test_add_and_query_returns_nearest_chunk(store: VectorStore) -> None:
    chunks = [_chunk("alpha", page=1, index=0), _chunk("beta", page=2, index=1), _chunk("gamma", page=3, index=2)]
    store.add_chunks(2, chunks, [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])

    assert store.count(2) == 3
    hits = store.query(2, [0.9, 0.1, 0.0], n_results=2)

    assert len(hits) == 2
    assert hits[0].text == "alpha"
    assert hits[0].page_number == 1
    assert hits[0].source_name == "notes.pdf"
    assert hits[0].chunk_id == "doc_2:0"


def test_query_missing_document_returns_empty(store: VectorStore) -> None:
    assert store.query(999, [1.0, 0.0, 0.0], n_results=5) == []


def test_all_chunks_ordered_by_page_then_index(store: VectorStore) -> None:
    chunks = [_chunk("second", page=2, index=1), _chunk("first", page=1, index=0)]
    store.add_chunks(7, chunks, [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])

    texts = [hit.text for hit in store.all_chunks(7)]
    assert texts == ["first", "second"]


def test_delete_collection_is_idempotent(store: VectorStore) -> None:
    store.add_chunks(3, [_chunk("x", page=1, index=0)], [[1.0, 0.0, 0.0]])
    assert store.count(3) == 1
    store.delete_collection(3)
    store.delete_collection(3)  # must not raise
    assert store.count(3) == 0


def test_embedding_model_mismatch_raises(tmp_path: Path) -> None:
    pytest.importorskip("chromadb")
    directory = str(tmp_path / "chroma")
    first = VectorStore(persistent_dir=directory, embedding_model="model-a")
    first.add_chunks(4, [_chunk("text", page=1, index=0)], [[1.0, 0.0, 0.0]])

    second = VectorStore(persistent_dir=directory, embedding_model="model-b")
    with pytest.raises(EmbeddingModelMismatchError):
        second.add_chunks(4, [_chunk("more", page=1, index=1)], [[0.0, 1.0, 0.0]])