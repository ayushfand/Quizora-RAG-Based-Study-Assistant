"""Persistent ChromaDB vector store, one collection per document.

Each collection records the embedding model it was built with. If a later
upload attempts to use a different embedding model, ingestion is refused with
:class:`EmbeddingModelMismatchError` so an index is never silently reused with
incompatible vectors (which would produce garbage retrieval).
"""

from __future__ import annotations

import os
from dataclasses import dataclass

os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")


@dataclass(frozen=True)
class StoredChunk:
    """A stored chunk retrieved from the vector store."""

    text: str
    chunk_id: str
    page_number: int
    chunk_index: int
    source_name: str
    score: float


class EmbeddingModelMismatchError(Exception):
    """Raised when chunks would be stored with a different embedding model."""


class VectorStore:
    """Thin, typed wrapper around a persistent ChromaDB client."""

    def __init__(self, persistent_dir: str, embedding_model: str) -> None:
        import chromadb

        self._client = chromadb.PersistentClient(path=persistent_dir)
        self.embedding_model = embedding_model

    @staticmethod
    def collection_name(document_id: int) -> str:
        return f"doc_{document_id}"

    # ------------------------------------------------------------ mutation

    def add_chunks(
        self,
        document_id: int,
        chunks: list,
        embeddings: list[list[float]],
    ) -> None:
        """Add chunks (with their precomputed embeddings) to the document collection."""
        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings must have the same length")
        if not chunks:
            return
        collection = self._get_or_create_collection(document_id)
        ids = [f"{self.collection_name(document_id)}:{chunk.chunk_index}" for chunk in chunks]
        documents = [chunk.text for chunk in chunks]
        metadatas = [
            {
                "page_number": chunk.page_number,
                "chunk_index": chunk.chunk_index,
                "source_name": chunk.source_name,
            }
            for chunk in chunks
        ]
        collection.add(ids=ids, documents=documents, metadatas=metadatas, embeddings=embeddings)

    def delete_collection(self, document_id: int) -> None:
        """Remove a document's collection (idempotent)."""
        from chromadb.errors import NotFoundError

        name = self.collection_name(document_id)
        try:
            self._client.delete_collection(name)
        except (ValueError, NotFoundError):
            pass  # collection did not exist

    # ------------------------------------------------------------ retrieval

    def count(self, document_id: int) -> int:
        collection = self._get_or_create_collection(document_id)
        return collection.count()

    def query(
        self,
        document_id: int,
        query_embedding: list[float],
        n_results: int,
    ) -> list[StoredChunk]:
        """Return the ``n_results`` most similar chunks to an embedding."""
        collection = self._get_or_create_collection(document_id)
        total = collection.count()
        if total == 0 or n_results <= 0:
            return []
        result = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(n_results, total),
            include=["documents", "metadatas", "distances"],
        )
        return self._build_hits(result)

    def all_chunks(self, document_id: int) -> list[StoredChunk]:
        """Return every chunk of a document ordered by page, then position."""
        collection = self._get_or_create_collection(document_id)
        data = collection.get(include=["documents", "metadatas"])
        hits: list[StoredChunk] = []
        ids = data.get("ids") or []
        documents = data.get("documents") or []
        metadatas = data.get("metadatas") or []
        for chunk_id, text, metadata in zip(ids, documents, metadatas):
            hits.append(
                StoredChunk(
                    text=text or "",
                    chunk_id=chunk_id,
                    page_number=int(metadata.get("page_number", 0)),
                    chunk_index=int(metadata.get("chunk_index", 0)),
                    source_name=str(metadata.get("source_name", "")),
                    score=0.0,
                )
            )
        hits.sort(key=lambda h: (h.page_number, h.chunk_index))
        return hits

    # -------------------------------------------------------------- helpers

    def _get_or_create_collection(self, document_id: int):
        name = self.collection_name(document_id)
        collection = self._client.get_or_create_collection(
            name=name,
            metadata={"embedding_model": self.embedding_model},
        )
        stored_model = (collection.metadata or {}).get("embedding_model")
        if stored_model and stored_model != self.embedding_model:
            raise EmbeddingModelMismatchError(
                f"Document already indexed with embedding model '{stored_model}', "
                f"but the current system uses '{self.embedding_model}'. "
                "Re-index the document or restore the previous embedding model."
            )
        return collection

    @staticmethod
    def _build_hits(result: dict) -> list[StoredChunk]:
        hits: list[StoredChunk] = []
        ids = (result.get("ids") or [[]])[0]
        documents = (result.get("documents") or [[]])[0]
        metadatas = (result.get("metadatas") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]
        for chunk_id, text, metadata, distance in zip(ids, documents, metadatas, distances):
            hits.append(
                StoredChunk(
                    text=text or "",
                    chunk_id=chunk_id,
                    page_number=int(metadata.get("page_number", 0)),
                    chunk_index=int(metadata.get("chunk_index", 0)),
                    source_name=str(metadata.get("source_name", "")),
                    score=float(distance),
                )
            )
        return hits