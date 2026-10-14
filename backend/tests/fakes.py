"""Shared fakes for the test suite (no external LLM required)."""

from __future__ import annotations

from app.llm.base import LLMProvider, ProviderHealth
from app.llm.errors import LLMError


class FakeProvider(LLMProvider):
    """Canned-response provider for deterministic LLM-layer tests.

    Each call pops the next response from ``responses``. If ``fail_on`` holds a
    call index, the call at that index raises ``error`` instead.
    """

    mode = "fake"

    def __init__(self, responses: list[str], fail_on: int | None = None, error: LLMError | None = None) -> None:
        super().__init__()
        self.responses = list(responses)
        self.fail_on = fail_on
        self.error = error
        self.calls: list[dict] = []

    @property
    def model_name(self) -> str:
        return "fake-model"

    def generate(self, prompt: str, system: str | None = None, temperature: float = 0.3) -> str:
        index = len(self.calls)
        self.calls.append({"prompt": prompt, "system": system, "temperature": temperature})
        if self.fail_on is not None and index == self.fail_on:
            raise self.error or LLMError("canned failure")
        if not self.responses:
            raise LLMError("FakeProvider ran out of canned responses")
        return self.responses.pop(0)

    def check_health(self) -> ProviderHealth:
        return ProviderHealth(mode=self.mode, available=True, default_model=self.model_name)