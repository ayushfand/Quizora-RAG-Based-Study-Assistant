"""Prompts for quiz generation.

Design rules implemented here:

- Questions must come ONLY from the provided source chunks.
- Difficulty is defined by cognitive level (recall → analysis).
- MCQ: exactly 4 options, one correct, plausible distractors, no
  "all of the above" / "none of the above".
- Short answer = 1–3 sentences; long answer = structured paragraph; both must
  include 3–6 key points and a reference answer.
- Generate in small batches (3–5 per LLM call) for local-model reliability;
  if the source material cannot support the requested count, fewer questions
  are acceptable — never invent facts.
"""

from __future__ import annotations

from ..rag.chunking import Chunk
from ..rag.vectorstore import StoredChunk

QUIZ_SYSTEM_PROMPT = (
    "You are an expert quiz author for students. You write precise, fair "
    "questions that are strictly grounded in the provided study material. "
    "You never invent facts, you never use material outside the source, and "
    "you always follow the requested format and difficulty constraints."
)

DIFFICULTY_GUIDE = """
Difficulty is defined by cognitive level:
- easy: recall and definition questions (who/what is, define, list, identify).
- medium: understanding, application, or comparison questions (explain how,
  give an example, compare X and Y).
- hard: analysis, multi-concept reasoning, or scenario-based questions
  (evaluate, predict what happens if, synthesize across sections).
""".strip()

QUESTION_TYPE_GUIDE = """
Question type requirements:
- mcq: exactly 4 plausible options with exactly one correct answer. Distractors
  must be plausible but clearly wrong. Never use "all of the above", "none of
  the above", or "both A and B". Provide an `explanation` of why the correct
  option is right.
- short_answer: answerable in 1-3 sentences. Provide a `reference_answer` and
  3-6 concise `key_points` that a complete answer must cover.
- long_answer: requires a structured paragraph or more. Provide a
  `reference_answer` and 3-6 `key_points` covering the main ideas.
""".strip()


def format_chunk(chunk: StoredChunk | Chunk, index: int) -> str:
    """Render one source chunk with its page number for the prompt."""
    return f"[Source #{index + 1} (page/slide {chunk.page_number})]\n{chunk.text}"


def build_batch_prompt(
    chunks: list[StoredChunk | Chunk],
    batch_size: int,
    question_types: list[str],
    difficulty: str,
    topic: str | None,
    context_char_limit: int = 8000,
) -> str:
    """Build the user prompt for one batch of question generation.

    Args:
        chunks: relevant source chunks (retrieved for the topic or sampled
            evenly across the document).
        batch_size: how many questions this batch should produce (3-5).
        question_types: e.g. ["mcq", "short_answer"].
        difficulty: easy | medium | hard.
        topic: optional topic/keyword focus.
        context_char_limit: cap on how much context is included, to keep small
            local models reliable and bounded in memory.
    """
    source_blocks: list[str] = []
    used = 0
    for index, chunk in enumerate(chunks):
        rendered = format_chunk(chunk, index)
        if used + len(rendered) > context_char_limit:
            break
        source_blocks.append(rendered)
        used += len(rendered)

    if topic and topic.strip():
        focus_line = (
            'The quiz must focus on the topic/keywords: "'
            + topic.strip()
            + '".\n'
            "If the source material does not cover this topic well, generate "
            "fewer questions — never invent content about the topic."
        )
    else:
        focus_line = "Cover the whole source material evenly."

    types_line = ", ".join(question_types)
    return f"""
Generate {batch_size} {difficulty} question(s) of type(s): {types_line}.

{focus_line}

SOURCE MATERIAL
===============
{chr(10).join(source_blocks)}

RULES
=====
- Base every question ONLY on the SOURCE MATERIAL above. Never use outside knowledge.
- If the source material cannot support {batch_size} high-quality questions,
  generate as many as it can support (fewer than {batch_size} is fine; questions
  must be answerable entirely from the source).
- Avoid repeating the same question in different wording.

{DIFFICULTY_GUIDE}

{QUESTION_TYPE_GUIDE}

OUTPUT FORMAT
=============
Respond with a single JSON object:
{{"questions": [ {{
  "type": "mcq" | "short_answer" | "long_answer",
  "difficulty": "{difficulty}",
  "text": "the question",
  "options": ["A", "B", "C", "D"],          // mcq only, exactly 4
  "correct_option": 0,                       // mcq only, 0-based index
  "reference_answer": "complete answer",     // open questions only
  "key_points": ["point 1", "point 2", ...], // open questions only, 3-6 items
  "explanation": "why the correct option is right"  // mcq only
}} ]}}
No markdown fences, no commentary before or after the JSON.
""".strip()