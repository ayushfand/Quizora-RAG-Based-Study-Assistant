"""Provider factory — pick an LLM backend by mode ("local" | "gemini")."""

from __future__ import annotations

from ..config import Settings, get_settings
from .base import LLMProvider
from .errors import LLMConfigurationError
from .gemini_provider import GeminiProvider
from .ollama_provider import OllamaProvider

SUPPORTED_MODES = ("local", "gemini")


class LLMFactory:
    """Creates and caches LLM providers, keyed by mode."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._providers: dict[str, LLMProvider] = {}

    def get_provider(self, mode: str | None = None) -> LLMProvider:
        """Return a provider for ``mode``, defaulting to DEFAULT_LLM_MODE.

        Raises :class:`LLMConfigurationError` for unknown modes. Providers are
        created lazily and cached, so repeated calls are cheap.
        """
        resolved = (mode or self.settings.default_llm_mode).strip().lower()
        if resolved not in SUPPORTED_MODES:
            raise LLMConfigurationError(
                f"Unknown LLM mode '{mode}'. Supported modes: {', '.join(SUPPORTED_MODES)}.",
                user_message=f"Unknown LLM mode '{mode}'. Choose 'local' or 'gemini'.",
            )
        if resolved not in self._providers:
            if resolved == "local":
                self._providers[resolved] = OllamaProvider(
                    base_url=self.settings.ollama_base_url,
                    model=self.settings.ollama_model,
                    timeout_seconds=self.settings.llm_timeout_seconds,
                    max_json_attempts=self.settings.llm_max_json_attempts,
                )
            else:
                self._providers[resolved] = GeminiProvider(
                    api_key=self.settings.gemini_api_key,
                    model=self.settings.gemini_model,
                    timeout_seconds=self.settings.llm_timeout_seconds,
                    max_json_attempts=self.settings.llm_max_json_attempts,
                )
        return self._providers[resolved]

    def available_modes(self) -> list[str]:
        """Return the modes configured on this machine."""
        return list(SUPPORTED_MODES)


_factory: LLMFactory | None = None


def get_provider(mode: str | None = None) -> LLMProvider:
    """Module-level access to the shared :class:`LLMFactory`."""
    global _factory
    if _factory is None:
        _factory = LLMFactory()
    return _factory.get_provider(mode)