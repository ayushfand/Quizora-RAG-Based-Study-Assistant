"""LLM provider abstraction: base class, Ollama, Gemini, and factory."""

from .base import LLMProvider, ProviderHealth
from .errors import (
    LLMAuthError,
    LLMConfigurationError,
    LLMConnectionError,
    LLMError,
    LLMModelNotFoundError,
    LLMRateLimitError,
    LLMStructuredOutputError,
    LLMTimeoutError,
)
from .factory import SUPPORTED_MODES, get_provider
from .utils import extract_json_text

__all__ = [
    "LLMAuthError",
    "LLMConfigurationError",
    "LLMConnectionError",
    "LLMError",
    "LLMModelNotFoundError",
    "LLMProvider",
    "LLMRateLimitError",
    "LLMStructuredOutputError",
    "LLMTimeoutError",
    "ProviderHealth",
    "SUPPORTED_MODES",
    "extract_json_text",
    "get_provider",
]