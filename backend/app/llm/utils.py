"""Helpers for working with raw LLM output."""

from __future__ import annotations

import json


def extract_json_text(raw: str) -> str | None:
    """Extract the first JSON value (object or array) from model output.

    Handles the common cases of models wrapping JSON in markdown code fences
    or surrounding it with prose. Returns the raw JSON substring, or None when
    no JSON value can be found.
    """
    if not raw:
        return None
    text = raw.strip()

    # Prefer the content of a markdown fenced code block when one is present.
    fenced = _extract_fenced_block(text)
    if fenced is not None:
        text = fenced.strip()

    if text[:1] in ("{", "[") and _is_balanced(text):
        return text

    candidates = [_scan_for(text, "{", "}"), _scan_for(text, "[", "]")]
    candidates = [c for c in candidates if c is not None]
    if not candidates:
        return None
    # Choose the value that starts earliest (the outermost JSON value); on a
    # tie prefer the shorter candidate.
    candidates.sort(key=lambda c: (text.index(c), len(c)))
    return candidates[0]


def _extract_fenced_block(text: str) -> str | None:
    """Return the inner text of the first ``` (or ```json) block, if any."""
    lines = text.splitlines()
    start: int | None = None
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.startswith("```"):
            continue
        lang = stripped[3:].strip().lower()
        if lang in ("", "json"):
            start = index
            break
    if start is None:
        return None
    inner: list[str] = []
    for line in lines[start + 1 :]:
        if line.strip().startswith("```"):
            return "\n".join(inner)
        inner.append(line)
    return "\n".join(inner) if inner else None


def _is_balanced(text: str) -> bool:
    """Return True when the text is exactly one complete JSON value."""
    try:
        json.loads(text)
        return True
    except json.JSONDecodeError:
        return False


def _scan_for(text: str, open_ch: str, close_ch: str) -> str | None:
    """Return the first balanced substring starting with open_ch, if any."""
    start = text.find(open_ch)
    if start == -1:
        return None
    depth = 0
    in_string = False
    escaped = False
    for i in range(start, len(text)):
        char = text[i]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == open_ch:
            depth += 1
        elif char == close_ch:
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None