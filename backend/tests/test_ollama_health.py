"""Unit tests for Ollama health/model matching (no live Ollama required)."""

from __future__ import annotations

import httpx
import pytest

from app.llm.ollama_provider import OllamaProvider, _same_model


class _FakeResponse:
    def __init__(self, payload: dict, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def json(self) -> dict:
        return self._payload


def _patch_tags(monkeypatch: pytest.MonkeyPatch, names: list[str]) -> None:
    def fake_get(url: str, timeout: float) -> _FakeResponse:
        return _FakeResponse({"models": [{"name": name} for name in names]})

    monkeypatch.setattr(httpx, "get", fake_get)


@pytest.mark.parametrize(
    ("configured", "reported", "expected"),
    [
        ("nomic-embed-text", "nomic-embed-text:latest", True),
        ("nomic-embed-text:latest", "nomic-embed-text", True),
        ("qwen2.5:7b-instruct", "qwen2.5:7b-instruct", True),
        ("qwen2.5:7b", "qwen2.5:7b-instruct", False),
        ("llama3", "nomic-embed-text:latest", False),
    ],
)
def test_same_model_matching(configured: str, reported: str, expected: bool) -> None:
    assert _same_model(configured, reported) is expected


def test_untagged_embed_model_is_reported_available(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_tags(monkeypatch, ["nomic-embed-text:latest", "qwen2.5:7b-instruct"])
    health = OllamaProvider(base_url="http://localhost:11434", model="nomic-embed-text").check_health()
    assert health.available is True
    assert health.default_model_available is True
    assert health.error is None


def test_missing_model_is_reported_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_tags(monkeypatch, ["qwen2.5:7b-instruct"])
    health = OllamaProvider(base_url="http://localhost:11434", model="llama3").check_health()
    assert health.available is True
    assert health.default_model_available is False
    assert "llama3" in (health.error or "")
