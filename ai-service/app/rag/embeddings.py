"""Embedding model (all-MiniLM-L6-v2, 384-d), loaded lazily once and batch-encoded.

Tests inject a fake embedder with :func:`set_embedder`. The first real use downloads ~90 MB (one time).
"""

from __future__ import annotations

import logging
import threading
from typing import Protocol

import numpy as np

log = logging.getLogger(__name__)
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
DIM = 384
_lock = threading.Lock()
_embedder: "Embedder | None" = None


class EmbedderUnavailable(RuntimeError):
    """The embedding model cannot be loaded (package missing, or the one-time ~90 MB download failed)."""


class Embedder(Protocol):
    dim: int

    def encode(self, texts: list[str]) -> np.ndarray: ...


class MiniLMEmbedder:
    """Thin wrapper over sentence-transformers (imported only when first used)."""

    dim = DIM

    def __init__(self, model_name: str = MODEL_NAME):
        from sentence_transformers import SentenceTransformer  # heavy import, deferred on purpose

        log.info("Loading embedding model %s ...", model_name)
        self._model = SentenceTransformer(model_name)

    def encode(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.dim), dtype=np.float32)
        vecs = self._model.encode(texts, batch_size=32, convert_to_numpy=True, normalize_embeddings=True, show_progress_bar=False)
        return np.asarray(vecs, dtype=np.float32)


def get_embedder() -> Embedder:
    global _embedder
    if _embedder is None:
        with _lock:
            if _embedder is None:
                try:
                    _embedder = MiniLMEmbedder()
                except Exception as exc:  # noqa: BLE001 - ImportError, offline first run, corrupt cache ...
                    raise EmbedderUnavailable(
                        f"The embedding model could not be loaded ({type(exc).__name__}: {str(exc)[:100]}). "
                        "The first run needs internet to download it (~90 MB); run ./scripts/setup.sh while online."
                    ) from exc
    return _embedder


def set_embedder(e: Embedder | None) -> None:
    """Replace (or reset with None) the process-wide embedder, used by tests."""
    global _embedder
    _embedder = e


def is_loaded() -> bool:
    return _embedder is not None


def warm_up() -> None:
    """Download/load the model now (called by scripts/setup.sh)."""
    get_embedder().encode(["warm up"])
