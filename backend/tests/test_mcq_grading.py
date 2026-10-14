"""Tests for deterministic MCQ grading."""

from __future__ import annotations

import pytest

from app.services.mcq import McqGrade, grade_mcq


def test_correct_answer_scores_full() -> None:
    grade = grade_mcq(correct_option=2, selected_option=2)
    assert isinstance(grade, McqGrade)
    assert grade.correct is True
    assert grade.score == 1.0


def test_wrong_answer_scores_zero() -> None:
    grade = grade_mcq(correct_option=2, selected_option=0)
    assert grade.correct is False
    assert grade.score == 0.0


def test_blank_answer_scores_zero() -> None:
    grade = grade_mcq(correct_option=2, selected_option=None)
    assert grade.correct is False
    assert grade.score == 0.0


def test_out_of_range_index_does_not_crash() -> None:
    grade = grade_mcq(correct_option=2, selected_option=999)
    assert grade.correct is False
    assert grade.score == 0.0


def test_question_without_correct_option_is_not_gradeable() -> None:
    grade = grade_mcq(correct_option=None, selected_option=0)
    assert grade.correct is False
    assert grade.score == 0.0