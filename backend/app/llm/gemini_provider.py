"""Gemini provider — uses the official google-genai SDK."""

from __future__ import annotations

from typing import Any

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

DEFAULT_MODEL = "gemini-2.0-flash"
DEFAULT_TIMEOUT_SECONDS = 180.0
HEALTH_TIMEOUT_SECONDS = 8.0


class GeminiProvider(LLMProvider):
    """LLM provider backed by the Google Gemini API.

    JSON schema response mode is handled with ``response_mime_type =
    "application/json"`` plus ``response_schema``; if the SDK cannot convert
    a schema we fall back to constrained-JSON output and let the base-class
    retry loop validate with Pydantic.
    """

    mode = "gemini"

    def __init__(
        self,
        api_key: str | None,
        model: str = DEFAULT_MODEL,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        max_json_attempts: int = 3,
    ) -> None:
        super().__init__(max_json_attempts=max_json_attempts)
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds
        self._client_obj: Any | None = None

    @property
    def model_name(self) -> str:
        return self.model

    # ------------------------------------------------------------------ API

    def generate(self, prompt: str, system: str | None = None, temperature: float = 0.3) -> str:
        client = self._client()
        config = self._config(system=system, temperature=temperature)
        try:
            response = client.models.generate_content(model=self.model, contents=prompt, config=config)
        except Exception as exc:  # noqa: BLE001 - mapped to typed errors below
            raise self._map_error(exc, "Gemini request failed") from exc
        text = (response.text or "").strip()
        if not text:
            raise LLMError(
                "Gemini returned an empty response.",
                user_message="Gemini returned an empty response. Try again or switch to Local mode.",
            )
        return text

    def _generate_structured(
        self,
        prompt: str,
        schema: type[BaseModel],
        schema_json: dict,
        system: str | None = None,
        temperature: float = 0.2,
    ) -> str:
        client = self._client()
        # Preference 1: native schema constraint.
        try:
            config = self._config(system=system, temperature=temperature, response_schema=schema)
            return self._structured_call(client, prompt, config)
        except LLMError:
            raise
        except Exception as exc:  # noqa: BLE001 - schema conversion may fail per SDK version
            # Preference 2: constrained JSON without an explicit schema; the
            # base class validates the text against the Pydantic schema.
            config = self._config(system=system, temperature=temperature, response_mime_type="application/json")
            try:
                return self._structured_call(client, prompt, config)
            except Exception as nested:  # noqa: BLE001
                raise self._map_error(nested, "Gemini structured request failed") from nested

    def check_health(self, timeout_seconds: float = HEALTH_TIMEOUT_SECONDS) -> ProviderHealth:
        if not self.api_key:
            return ProviderHealth(
                mode=self.mode,
                available=False,
                default_model=self.model,
                error="GEMINI_API_KEY is not set in backend/.env. Gemini mode is unavailable.",
            )
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=self.api_key, http_options=types.HttpOptions(timeout=int(timeout_seconds * 1000)))
            client.models.get(model=self.model)
        except Exception as exc:  # noqa: BLE001
            mapped = self._map_error(exc, "Gemini health check failed")
            return ProviderHealth(
                mode=self.mode,
                available=False,
                default_model=self.model,
                error=mapped.user_message,
            )
        return ProviderHealth(
            mode=self.mode,
            available=True,
            models=[self.model],
            default_model=self.model,
            default_model_available=True,
        )

    # --------------------------------------------------------------- helpers

    def _require_key(self) -> None:
        if not self.api_key:
            raise LLMAuthError(
                "Gemini API key is missing.",
                user_message="Gemini API key is missing. Set GEMINI_API_KEY in backend/.env to use Gemini mode.",
            )

    def _client(self) -> Any:
        if self._client_obj is None:
            self._require_key()
            try:
                from google import genai
                from google.genai import types
            except ImportError as exc:
                raise LLMError(
                    "The 'google-genai' package is not installed.",
                    user_message="The google-genai package is missing. Run: pip install -r backend/requirements.txt",
                ) from exc
            self._client_obj = genai.Client(
                api_key=self.api_key,
                http_options=types.HttpOptions(timeout=int(self.timeout_seconds * 1000)),
            )
        return self._client_obj

    def _config(
        self,
        system: str | None,
        temperature: float,
        response_schema: Any | None = None,
        response_mime_type: str | None = None,
    ) -> Any:
        from google.genai import types

        kwargs: dict[str, Any] = {"temperature": temperature}
        if system:
            kwargs["system_instruction"] = system
        if response_mime_type:
            kwargs["response_mime_type"] = response_mime_type
        if response_schema is not None:
            kwargs["response_mime_type"] = "application/json"
            kwargs["response_schema"] = response_schema
        return types.GenerateContentConfig(**kwargs)

    def _structured_call(self, client: Any, prompt: str, config: Any) -> str:
        response = client.models.generate_content(model=self.model, contents=prompt, config=config)
        return (response.text or "").strip()

    def _map_error(self, exc: Exception, prefix: str = "Gemini API error") -> LLMError:
        """Translate google-genai / httpx exceptions into typed LLM errors."""
        try:
            from google.genai import errors as genai_errors
        except ImportError:
            genai_errors = None  # type: ignore[assignment]

        if genai_errors is not None and isinstance(exc, genai_errors.APIError):
            code = getattr(exc, "code", None)
            message = getattr(exc, "message", None) or str(exc)
            if code == 429:
                return LLMRateLimitError(
                    f"{prefix}: HTTP 429 rate limit: {message[:300]}",
                    user_message="Gemini hit its rate limit. Wait a moment and try again, or switch to Local (Ollama) mode.",
                )
            if code in (401, 403):
                return LLMAuthError(
                    f"{prefix}: HTTP {code} auth failure: {message[:300]}",
                    user_message="Gemini authentication failed. Check GEMINI_API_KEY in backend/.env.",
                )
            if code == 404 or (code == 400 and "not found" in message.lower() and "model" in message.lower()):
                return LLMModelNotFoundError(
                    f"{prefix}: model '{self.model}' not found (HTTP {code}): {message[:200]}",
                    user_message=f"Gemini model '{self.model}' is not available. Check GEMINI_MODEL in backend/.env.",
                )
            return LLMError(
                f"{prefix}: HTTP {code} {message[:300]}",
                user_message=f"Gemini API error (HTTP {code}). {message[:200]}",
            )
        if isinstance(exc, httpx.TimeoutException):
            return LLMTimeoutError(
                f"{prefix}: request timed out.",
                user_message=(
                    f"Gemini did not answer within {self.timeout_seconds:.0f}s. "
                    "Try again or switch to Local mode."
                ),
            )
        if isinstance(exc, (httpx.HTTPError, ConnectionError)):
            return LLMConnectionError(
                f"{prefix}: network error while reaching the Gemini API.",
                user_message="Could not reach the Gemini API. Check your internet connection.",
            )
        return LLMError(
            f"{prefix}: {str(exc)[:300]}",
            user_message=f"Gemini error: {str(exc)[:200]}",
        )