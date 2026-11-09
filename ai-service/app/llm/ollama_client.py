"""Minimal Ollama HTTP client (local LLM). Every failure raises :class:`LLMUnavailable`."""

from __future__ import annotations

import json
import logging

import httpx

from ..config import get_settings

log = logging.getLogger(__name__)


class LLMUnavailable(RuntimeError):
    """Ollama is down, the model is missing, or the call timed out."""


def is_available() -> bool:
    s = get_settings()
    try:
        r = httpx.get(f"{s.ollama_url.rstrip('/')}/api/tags", timeout=1.5)
        names = [m.get("name", "") for m in r.json().get("models", [])]
        return any(n == s.ollama_model or n.startswith(s.ollama_model + ":") for n in names)
    except Exception:  # noqa: BLE001
        return False


def generate(
    system: str, prompt: str, *, json_mode: bool = False, temperature: float = 0.2, timeout: float = 90.0, retries: int = 1
) -> str:
    """Single-turn completion. Temperature defaults to 0.2; one retry on transient failure."""
    s = get_settings()
    body = {
        "model": s.ollama_model,
        "stream": False,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
        "options": {"temperature": temperature, "num_ctx": 4096},
    }
    if json_mode:
        body["format"] = "json"
    last: Exception | None = None
    for attempt in range(retries + 1):
        try:
            r = httpx.post(f"{s.ollama_url.rstrip('/')}/api/chat", json=body, timeout=httpx.Timeout(timeout, connect=3.0))
            r.raise_for_status()
            return r.json()["message"]["content"]
        except Exception as exc:  # noqa: BLE001
            last = exc
            log.warning("Ollama call failed (attempt %d): %s", attempt + 1, exc)
    raise LLMUnavailable(f"Ollama unavailable: {last}")


def generate_json(system: str, prompt: str, **kw) -> object:
    """Like :func:`generate` but parses JSON; raises LLMUnavailable on invalid JSON."""
    raw = generate(system, prompt, json_mode=True, **kw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise LLMUnavailable(f"Model returned invalid JSON: {exc}") from exc
