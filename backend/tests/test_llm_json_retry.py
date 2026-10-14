"""Tests for structured JSON generation (retry + validation in the base class).

Uses a fake provider with canned responses so no real LLM is required.
"""

from __future__ import annotations

import pytest
from pydantic import BaseModel

from app.llm.base import ProviderHealth
from app.llm.errors import LLMStructuredOutputError
from app.llm.utils import extract_json_text

from .fakes import FakeProvider


class Recipe(BaseModel):
    """Simple schema used to exercise structured generation."""

    name: str
    servings: int
    ingredients: list[str]


def test_generate_json_gives_up_and_raises_after_max_attempts() -> None:
    provider = FakeProvider(["no", "still no", "definitely no"])
    with pytest.raises(LLMStructuredOutputError) as exc_info:
        provider.generate_json("Write a recipe", Recipe)
    assert len(provider.calls) == 3
    assert "fake-model" in str(exc_info.value)
    assert "Recipe" in str(exc_info.value)
    raw = 'Sure! Here is the result:\n```json\n{"name": "Pancakes", "servings": 2, "ingredients": ["flour"]}\n```\n'
    extracted = extract_json_text(raw)
    assert extracted is not None
    assert Recipe.model_validate_json(extracted).name == "Pancakes"


def test_extract_json_text_returns_none_for_prose() -> None:
    assert extract_json_text("I do not have an answer for you.") is None


def test_generate_json_succeeds_on_first_attempt() -> None:
    provider = FakeProvider(['{"name": "Pancakes", "servings": 2, "ingredients": ["flour", "egg"]}'])
    result = provider.generate_json("Write a recipe", Recipe)
    assert isinstance(result, Recipe)
    assert result.name == "Pancakes"
    assert result.servings == 2
    assert len(provider.calls) == 1


def test_generate_json_retries_with_feedback_and_succeeds() -> None:
    provider = FakeProvider(
        [
            "Sorry, I cannot do that.",  # no JSON at all
            '```json\n{"name": "Omelette", "servings": 1, "ingredients": ["egg", "cheese"]}\n```',
        ]
    )
    result = provider.generate_json("Write a recipe", Recipe)
    assert result.name == "Omelette"
    assert len(provider.calls) == 2
    # The retry prompt must include the validation feedback.
    assert "did not validate" in provider.calls[1]["prompt"]


def test_generate_json_feeds_pydantic_errors_back() -> None:
    provider = FakeProvider(
        [
            '{"name": 123, "servings": "two", "ingredients": "flour"}',  # fails type validation
            '{"name": "Soup", "servings": 4, "ingredients": ["water", "salt"]}',
        ]
    )
    result = provider.generate_json("Write a recipe", Recipe)
    assert result.name == "Soup"
    assert len(provider.calls) == 2
    assert "did not validate" in provider.calls[1]["prompt"]


def test_generate_json_gives_up_and_raises_after_max_attempts() -> None:
    provider = FakeProvider(["no", "still no", "definitely no"])
    with pytest.raises(LLMStructuredOutputError) as exc_info:
        provider.generate_json("Write a recipe", Recipe)
    assert len(provider.calls) == 3
    assert "fake-model" in str(exc_info.value)
    assert "Recipe" in str(exc_info.value)