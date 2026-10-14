"""Exception hierarchy for the LLM layer.

Every exception carries a `user_message` suitable for direct display in the
UI, so backend handlers can translate provider failures into friendly errors.
"""

from __future__ import annotations


class LLMError(Exception):
    """Base class for all errors raised by the LLM layer."""

    def __init__(self, message: str, user_message: str | None = None) -> None:
        super().__init__(message)
        self._user_message = user_message or message

    @property
    def user_message(self) -> str:
        """Human-readable message safe to show to end users."""
        return self._user_message


class LLMConfigurationError(LLMError):
    """Bad configuration (unknown mode, empty model name, ...)."""


class LLMConnectionError(LLMError):
    """The provider endpoint could not be reached."""


class LLMTimeoutError(LLMError):
    """The provider did not respond within the configured timeout."""


class LLMAuthError(LLMError):
    """Missing/invalid API key or expired credentials."""


class LLMRateLimitError(LLMError):
    """The provider returned a rate-limit / quota error."""


class LLMModelNotFoundError(LLMError):
    """The configured model is not available on the provider."""


class LLMStructuredOutputError(LLMError):
    """The model repeatedly failed to produce valid JSON for a schema."""