"""Prompt templates for Quizora — RAG based study assistant (files/constants, never inline strings)."""

from .evaluation import (
    EVALUATION_SYSTEM_PROMPT,
    PROMPT_INJECTION_GUARD,
    build_evaluation_prompt,
)
from .quiz_generation import DIFFICULTY_GUIDE, QUESTION_TYPE_GUIDE, QUIZ_SYSTEM_PROMPT, build_batch_prompt

__all__ = [
    "DIFFICULTY_GUIDE",
    "EVALUATION_SYSTEM_PROMPT",
    "PROMPT_INJECTION_GUARD",
    "QUESTION_TYPE_GUIDE",
    "QUIZ_SYSTEM_PROMPT",
    "build_batch_prompt",
    "build_evaluation_prompt",
]