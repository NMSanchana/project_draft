"""Prompt-injection / code-execution guard. Dataset and document text is always untrusted."""

from __future__ import annotations

import re

_PATTERNS = [
    r"ignore (all |any |the )?(previous|prior|above|earlier) (instructions|rules|prompts?)",
    r"disregard (all |any |the )?(previous|prior|above|your) (instructions|rules|prompts?)",
    r"(reveal|show|print|display|repeat|tell me|output|leak) (me )?(your|the) (system |hidden |initial )?(prompt|instructions|rules)",
    r"system prompt",
    r"you are now\b",
    r"\b(act|pretend|behave) (as|like) (a |an )?(different|unrestricted|dan|developer)",
    r"developer mode|jailbreak|\bdan mode\b",
    r"\b(run|execute|eval|exec)\b.{0,40}\b(python|code|script|command|shell|bash|sql|javascript)\b",
    r"\b(python|bash|shell|sql)\b.{0,15}(code|script)?.{0,20}\b(run|execute)\b",
    r"```",
    r"\bimport (os|sys|subprocess)\b",
    r"__import__|\beval\(|\bexec\(|os\.system|subprocess\.",
    r"\brm -rf\b|\bdrop table\b|;\s*delete from\b",
]
_RX = re.compile("|".join(f"(?:{p})" for p in _PATTERNS), re.I | re.S)

REFUSAL = (
    "I can't follow instructions that try to change my rules or run code. "
    "I can answer questions about your sales data, the ML insights, and your uploaded documents."
)


def is_injection(text: str) -> bool:
    return bool(_RX.search(text or ""))


def sanitize_context(text: str) -> str:
    """Remove lines of retrieved document text that look like instructions to the model."""
    kept = [ln for ln in text.splitlines() if not _RX.search(ln)]
    return "\n".join(kept).strip()
