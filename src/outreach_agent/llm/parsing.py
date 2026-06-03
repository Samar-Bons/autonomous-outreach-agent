# ABOUTME: Small shared helpers for parsing model responses.
# ABOUTME: One home for code-fence stripping, used by every JSON response parser.
from __future__ import annotations


def strip_code_fences(text: str) -> str:
    """Strip a leading ```lang fence and trailing ``` from a model response."""
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[-1]
        if t.endswith("```"):
            t = t.rsplit("```", 1)[0]
    return t.strip()
