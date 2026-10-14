"""Schemas for the quiz-generation LLM output (validated with Pydantic)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class GeneratedQuestion(BaseModel):
    """One question as produced by the LLM (validated before persisting)."""

    type: Literal["mcq", "short_answer", "long_answer"]
    difficulty: Literal["easy", "medium", "hard"]
    text: str = Field(min_length=5, max_length=1500)
    options: list[str] | None = Field(default=None)
    correct_option: int | None = Field(default=None, ge=0, le=3)
    reference_answer: str | None = Field(default=None, max_length=3000)
    key_points: list[str] | None = Field(default=None)
    explanation: str | None = Field(default=None, max_length=1500)

    @model_validator(mode="before")
    @classmethod
    def _sanitize_llm_fields(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data
        q_type = data.get("type")
        if q_type == "mcq":
            # For MCQ, empty key_points should be ignored
            if isinstance(data.get("key_points"), list) and not data["key_points"]:
                data["key_points"] = None
            opts = data.get("options")
            if isinstance(opts, list):
                # Clean options
                data["options"] = [str(o).strip() for o in opts if str(o).strip()][:4]
        elif q_type in ("short_answer", "long_answer"):
            # For open questions, empty options should be None
            if isinstance(data.get("options"), list) and not data["options"]:
                data["options"] = None
            kpoints = data.get("key_points")
            if isinstance(kpoints, list):
                cleaned = [str(k).strip() for k in kpoints if str(k).strip()][:8]
                data["key_points"] = cleaned if cleaned else None
            # If key_points is missing but reference_answer exists, supply fallback
            if not data.get("key_points") and data.get("reference_answer"):
                ref = str(data["reference_answer"]).strip()
                if ref:
                    data["key_points"] = [ref[:200]]
        return data

    @model_validator(mode="after")
    def _check_type_consistency(self) -> "GeneratedQuestion":
        if self.type == "mcq":
            if not self.options or len(self.options) < 4 or self.correct_option is None:
                raise ValueError("mcq questions require exactly 4 options and a correct_option index (0-3)")
        else:
            if not self.reference_answer:
                raise ValueError("open questions require a reference_answer")
            if not self.key_points or len(self.key_points) == 0:
                raise ValueError("open questions require at least one key point")
        return self


class QuestionBatch(BaseModel):
    """Structured output for one generation call (a small batch)."""

    questions: list[GeneratedQuestion] = Field(default_factory=list, min_length=1, max_length=5)


class AnswerEvaluation(BaseModel):
    """LLM-as-judge output for one open-ended answer (validated before persisting)."""

    score: float = Field(ge=0.0, le=10.0)
    covered_points: list[str] = Field(default_factory=list, max_length=20)
    missed_points: list[str] = Field(default_factory=list, max_length=20)
    feedback: str = Field(min_length=1, max_length=4000)
    model_answer: str | None = Field(default=None, max_length=4000)