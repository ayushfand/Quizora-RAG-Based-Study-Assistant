"""Ollama provider — talks to a local Ollama server over its HTTP API."""

from __future__ import annotations

import httpx
from pydantic import BaseModel

from .base import LLMProvider, ProviderHealth
from .errors import (
    LLMAuthError,
    LLMConnectionError,
    LLMError,
    LLMModelNotFoundError,
    LLMRateLimitError,
    LLMTimeoutError,
)

DEFAULT_TIMEOUT_SECONDS = 180.0
HEALTH_TIMEOUT_SECONDS = 5.0


def _with_implicit_tag(name: str) -> str:
    """Ollama reports untagged models as ``<name>:latest``; normalize both sides."""
    return name if ":" in name else f"{name}:latest"


def _same_model(configured: str, reported: str) -> bool:
    """True when two Ollama model references point at the same model/tag."""
    return configured == reported or _with_implicit_tag(configured) == _with_implicit_tag(reported)


class OllamaProvider(LLMProvider):
    """LLM provider backed by a local Ollama server (``/api/chat``)."""

    mode = "local"

    def __init__(
        self,
        base_url: str,
        model: str,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        max_json_attempts: int = 3,
    ) -> None:
        super().__init__(max_json_attempts=max_json_attempts)
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds
        if not self.model:
            raise LLMError("OLLAMA_MODEL is not configured. Set it in backend/.env.")

    @property
    def model_name(self) -> str:
        return self.model

    # ------------------------------------------------------------------ API

    def generate(self, prompt: str, system: str | None = None, temperature: float = 0.3) -> str:
        messages = self._messages(prompt, system)
        return self._chat(messages=messages, temperature=temperature)

    def _generate_structured(
        self,
        prompt: str,
        schema: type[BaseModel],
        schema_json: dict,
        system: str | None = None,
        temperature: float = 0.2,
    ) -> str:
        # Ollama's `format` parameter constrains the response to a JSON schema.
        messages = self._messages(prompt, system)
        return self._chat(messages=messages, temperature=temperature, format=schema_json)

    def check_health(self, timeout_seconds: float = HEALTH_TIMEOUT_SECONDS) -> ProviderHealth:
        url = f"{self.base_url}/api/tags"
        try:
            response = httpx.get(url, timeout=timeout_seconds)
        except httpx.TimeoutException:
            return ProviderHealth(
                mode=self.mode,
                available=False,
                default_model=self.model,
                error=f"Ollama health check timed out at {self.base_url}.",
            )
        except httpx.HTTPError:
            return ProviderHealth(
                mode=self.mode,
                available=False,
                default_model=self.model,
                error=(
                    "Ollama is not reachable. Is it running? "
                    f"Start it with `ollama serve` (checked {self.base_url})."
                ),
            )
        if response.status_code != 200:
            return ProviderHealth(
                mode=self.mode,
                available=False,
                default_model=self.model,
                error=f"Ollama /api/tags returned HTTP {response.status_code}.",
            )
        names = sorted({str(model.get("name", "")) for model in response.json().get("models", []) if model.get("name")})
        default_ok = any(_same_model(self.model, name) for name in names)
        return ProviderHealth(
            mode=self.mode,
            available=True,
            models=names,
            default_model=self.model,
            default_model_available=default_ok,
            error=None if default_ok else f"Model '{self.model}' is not pulled. Run: ollama pull {self.model}",
        )

    # --------------------------------------------------------------- helpers

    def _messages(self, prompt: str, system: str | None) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        return messages

    def _chat(self, messages: list[dict[str, str]], temperature: float, format: dict | None = None) -> str:
        payload: dict = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature},
        }
        if format is not None:
            payload["format"] = format
        url = f"{self.base_url}/api/chat"
        try:
            response = httpx.post(url, json=payload, timeout=self.timeout_seconds)
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError(
                f"Ollama request timed out after {self.timeout_seconds}s (model '{self.model}').",
                user_message=(
                    f"Ollama did not answer within {self.timeout_seconds:.0f}s. "
                    "The model may still be loading weights; try again."
                ),
            ) from exc
        except httpx.HTTPError as exc:
            raise LLMConnectionError(
                f"Could not reach Ollama at {self.base_url}: {exc}",
                user_message="Ollama is not reachable. Is it running? Start it with `ollama serve`.",
            ) from exc
        if response.status_code != 200:
            self._raise_for_status(response)
        data = response.json()
        content = (data.get("message") or {}).get("content", "")
        if not content:
            raise LLMError(
                f"Ollama returned an empty response for model '{self.model}'.",
                user_message="Ollama returned an empty response. Try again or select a different model.",
            )
        return content

    def _raise_for_status(self, response: httpx.Response) -> None:
        error_text = ""
        try:
            error_text = str((response.json() or {}).get("error", response.text))[:300]
        except ValueError:
            error_text = response.text[:300]
        lowered = error_text.lower()
        if response.status_code == 429:
            raise LLMRateLimitError(
                f"Ollama rate limited the request: {error_text}",
                user_message="Ollama is busy. Wait a moment and try again.",
            )
        if response.status_code in (401, 403):
            raise LLMAuthError(
                f"Ollama rejected the request: {error_text}",
                user_message="Ollama rejected the request (authentication/authorization). Check its configuration.",
            )
        if "not found" in lowered and ("model" in lowered or response.status_code == 404):
            raise LLMModelNotFoundError(
                f"Ollama model '{self.model}' not found: {error_text}",
                user_message=f"Model '{self.model}' is not available in Ollama. Run: ollama pull {self.model}",
            )
        raise LLMError(
            f"Ollama returned HTTP {response.status_code}: {error_text}",
            user_message=f"Ollama error (HTTP {response.status_code}). {error_text}",
        )