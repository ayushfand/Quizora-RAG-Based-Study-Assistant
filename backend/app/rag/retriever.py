"""Retrieval: pick source chunks for quiz generation.

Two modes:

- With a topic: embed the topic text and return the most similar chunks.
- Without a topic: sample chunks evenly across the whole document so generated
  questions cover all sections instead of clustering on the first pages.
"""

from __future__ import annotations

import math

from .embeddings import EmbeddingProvider
from .vectorstore import StoredChunk, VectorStore


class Retriever:
    """Retrieves source chunks for a document, topic-aware or whole-document."""

    def __init__(self, vectorstore: VectorStore, embedder: EmbeddingProvider) -> None:
        self.vectorstore = vectorstore
        self.embedder = embedder

    def retrieve(
        self,
        document_id: int,
        topic: str | None,
        max_chunks: int,
    ) -> list[StoredChunk]:
        """Return up to ``max_chunks`` source chunks for quiz generation.

        Args:
            document_id: target document in the vector store.
            topic: optional topic/keyword focus; when provided, semantic search.
            max_chunks: maximum number of chunks to return.

        Returns:
            Relevant chunks ordered by relevance (topic mode) or reading order
            (even coverage mode).
        """
        if max_chunks <= 0:
            return []
        if topic and topic.strip():
            query_embedding = self.embedder.embed([topic.strip()])[0]
            hits = self.vectorstore.query(document_id, query_embedding, n_results=max_chunks)
            if hits:
                return hits
            # Topic search found nothing (empty collection) — fall through.
        all_chunks = self.vectorstore.all_chunks(document_id)
        return _sample_evenly(all_chunks, max_chunks)


def _sample_evenly(chunks: list[StoredChunk], count: int) -> list[StoredChunk]:
    """Pick ``count`` chunks spaced evenly across ``chunks`` (reading order)."""
    if not chunks:
        return []
    if count >= len(chunks):
        return chunks
    step = (len(chunks) - 1) / (count - 1) if count > 1 else 0
    indices = {round(i * step) for i in range(count)}
    return [chunks[i] for i in sorted(indices)]