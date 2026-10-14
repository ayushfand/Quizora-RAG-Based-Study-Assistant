"""Pluggable embedding providers.

The embedding provider is independent from the generation-mode LLM provider:
documents are always embedded with Ollama's ``nomic-embed-text`` (configurable
via OLLAMA_EMBED_MODEL), so switching Local/Gemini never re-indexes.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import httpx

from ..llm.errors import LLMConnectionError, LLMError, LLMTimeoutError

DEFAULT_BATCH_SIZE = 32


class EmbeddingProvider(ABC):
    """Base class for text embedding providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Identifier of the provider + model, e.g. 'ollama/nomic-embed-text'."""

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding vector per input text, preserving order."""


class OllamaEmbeddingProvider(EmbeddingProvider):
    """Embedding provider backed by Ollama's ``/api/embed`` endpoint."""

    def __init__(
        self,
        base_url: str,
        model: str,
        timeout_seconds: float = 120.0,
        batch_size: int = DEFAULT_BATCH_SIZE,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.batch_size = max(1, batch_size)
        if not self.model:
            raise LLMError("OLLAMA_EMBED_MODEL is not configured. Set it in backend/.env.")

    @property
    def name(self) -> str:
        return f"ollama/{self.model}"

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of texts in batches to bound memory usage."""
        results: list[list[float]] = []
        for start in range(0, len(texts), self.batch_size):
            batch = texts[start : start + self.batch_size]
            results.extend(self._embed_batch(batch))
        return results

    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        url = f"{self.base_url}/api/embed"
        payload = {"model": self.model, "input": texts}
        try:
            response = httpx.post(url, json=payload, timeout=self.timeout_seconds)
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError(
                f"Ollama embedding request timed out after {self.timeout_seconds:.0f}s.",
                user_message="Embedding request timed out. Try uploading the document again.",
            ) from exc
        except httpx.HTTPError as exc:
            raise LLMConnectionError(
                f"Could not reach Ollama at {self.base_url}: {exc}",
                user_message="Ollama is not reachable. Start it with `ollama serve`.",
            ) from exc
        if response.status_code != 200:
            message = ""
            try:
                message = str((response.json() or {}).get("error", ""))[:300]
            except ValueError:
                message = response.text[:300]
            raise LLMError(
                f"Ollama /api/embed returned HTTP {response.status_code}: {message}",
                user_message=(
                    f"Embedding failed (HTTP {response.status_code}): {message} "
                    "If the model is missing, run: ollama pull nomic-embed-text"
                ),
            )
        data = response.json()
        embeddings = data.get("embeddings")
        if not isinstance(embeddings, list) or len(embeddings) != len(texts):
            raise LLMError(
                f"Ollama /api/embed returned an unexpected payload for model '{self.model}'.",
                user_message="Embedding service returned an unexpected response.",
            )
        return [list(map(float, emb)) for emb in embeddings]