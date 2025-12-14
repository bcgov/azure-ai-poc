"""Text utilities shared across services.

Keep prompt-shaping and trimming logic consistent across agents.
"""

from __future__ import annotations

from textwrap import shorten

# Common prompt/cost guard used by multiple agents
MAX_HISTORY_CHARS = 1200


def trim_text(text: str, max_chars: int) -> str:
    """Trim text to reduce prompt size while keeping readability."""
    if not text:
        return text
    if max_chars <= 0:
        return ""
    if len(text) <= max_chars:
        return text

    return shorten(text, width=max_chars, placeholder=" …")
