"""Abstract LLM provider contract shared by Ollama and Gemini backends."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod

from pydantic import BaseModel, Field

from .errors import LLMStructuredOutputError
from .utils import extract_json_text


class ProviderHealth(BaseModel):
    """Availability report for a single LLM provider, used by /api/health."""

    mode: str
    available: bool
    models: list[str] = Field(default_factory=list)
    default_model: str = ""
    default_model_available: bool = False
    error: str | None = None


class LLMProvider(ABC):
    """Base class for LLM providers.

    Implementations only need to provide `generate` (plain text completion),
    `model_name`, `mode`, and `check_health`. `generate_json` is implemented
    here: it asks the model for JSON against a Pydantic schema, validates the
    result, and retries up to ``max_json_attempts`` times, feeding the
    validation error back to the model between attempts.
    """

    mode: str = "unknown"
    structured_output_temperature: float = 0.2

    def __init__(self, max_json_attempts: int = 3) -> None:
        self.max_json_attempts = max(1, int(max_json_attempts))

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Name of the model this provider talks to."""

    @abstractmethod
    def generate(self, prompt: str, system: str | None = None, temperature: float = 0.3) -> str:
        """Return a plain-text completion for ``prompt``."""

    @abstractmethod
    def check_health(self) -> ProviderHealth:
        """Probe the provider and report availability (never raises)."""

    def generate_json(
        self,
        prompt: str,
        schema: type[BaseModel],
        system: str | None = None,
        temperature: float | None = None,
    ) -> BaseModel:
        """Return a validated Pydantic instance matching ``schema``.

        Retries up to ``self.max_json_attempts`` times. On every failure the
        validation error is appended to the prompt so the model can correct
        itself. Raises :class:`LLMStructuredOutputError` when all attempts fail.
        """
        effective_temperature = temperature if temperature is not None else self.structured_output_temperature
        schema_json = schema.model_json_schema()
        last_error: str | None = None
        working_prompt = prompt

        for attempt in range(1, self.max_json_attempts + 1):
            if last_error is not None:
                working_prompt = (
                    f"{prompt}\n\n"
                    "Note from the system: the JSON you previously returned did not validate. "
                    f"Validation error: {last_error}\n"
                    "Respond with ONLY a single valid JSON document matching this schema exactly:\n"
                    f"{json.dumps(schema_json)}\n"
                    "No markdown fences, no commentary before or after the JSON."
                )
            raw = self._generate_structured(working_prompt, schema, schema_json, system, effective_temperature)
            candidate = extract_json_text(raw)
            if candidate is None:
                last_error = f"Could not find a JSON value in the model output: {raw[:200]!r}"
                continue
            try:
                parsed = json.loads(candidate)
                return schema.model_validate(parsed)
            except (json.JSONDecodeError, ValueError) as exc:  # noqa: BLE001 - ValidationError subclasses ValueError
                last_error = f"{type(exc).__name__}: {str(exc)[:500]}"

        raise LLMStructuredOutputError(
            f"Model '{self.model_name}' failed to produce valid JSON matching schema "
            f"'{schema.__name__}' after {self.max_json_attempts} attempts. "
            f"Last validation error: {last_error}"
        )

    def _generate_structured(
        self,
        prompt: str,
        schema: type[BaseModel],
        schema_json: dict,
        system: str | None = None,
        temperature: float = 0.2,
    ) -> str:
        """Provider hook for structured output.

        Default behaviour is a plain call to :meth:`generate`. Providers that
        support native schema constraints (Ollama ``format``, Gemini
        ``response_schema``) override this while keeping the retry logic in
        the base class.
        """
        return self.generate(prompt, system=system, temperature=temperature)