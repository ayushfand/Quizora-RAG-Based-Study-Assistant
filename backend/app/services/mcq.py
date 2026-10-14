"""Deterministic MCQ grading.

MCQ answers are graded by comparing the selected option index to the stored
correct option index. The score is normalized to 1.0 so the evaluator can
scale it to a uniform 0–10 scale along with open-ended questions.
"""

from __future__ import annotations

from pydantic import BaseModel


class McqGrade(BaseModel):
    """Result of grading a single MCQ answer."""

    selected_option: int | None
    correct_option: int | None
    correct: bool
    score: float  # 1.0 for a correct choice, 0.0 otherwise


def grade_mcq(correct_option: int | None, selected_option: int | None) -> McqGrade:
    """Grade an MCQ by comparing the selected option index to the correct one.

    Args:
        correct_option: index (0-based) of the correct option, if known.
        selected_option: index (0-based) the student chose, or None if blank.

    Returns:
        An :class:`McqGrade` with a deterministic 1.0 / 0.0 score.
    """
    if correct_option is None:
        return McqGrade(selected_option=selected_option, correct_option=None, correct=False, score=0.0)
    if selected_option is None or selected_option != correct_option:
        return McqGrade(
            selected_option=selected_option,
            correct_option=correct_option,
            correct=False,
            score=0.0,
        )
    return McqGrade(selected_option=selected_option, correct_option=correct_option, correct=True, score=1.0)