"""Deterministic test doubles for the embedder and Qdrant."""

from __future__ import annotations

import hashlib
import re

import numpy as np

_STOP = set(
    "a an the of to in on for and or is are was were be it its this that with as at by from what which who how do does did can "
    "could should would will my our your i we you they about any there their if not no".split()
)


class HashEmbedder:
    """Hashed bag-of-words vectors (384-d, L2-normalised). Related texts share words, hence similarity.

    This tests the *pipeline* (chunk -> embed -> Qdrant -> retrieve -> rerank). It says nothing about the
    quality of the real MiniLM model, which cannot be downloaded in the build sandbox.
    """

    dim = 384

    def encode(self, texts: list[str]) -> np.ndarray:
        out = np.zeros((len(texts), self.dim), dtype=np.float32)
        for i, t in enumerate(texts):
            for w in re.findall(r"[a-z0-9]+", t.lower()):
                if w in _STOP or len(w) < 2:
                    continue
                w = w[:-1] if w.endswith("s") and len(w) > 3 else w
                h = int(hashlib.md5(w.encode()).hexdigest(), 16)
                out[i, h % self.dim] += 1.0 if (h >> 8) % 2 == 0 else -1.0 * 0 + 1.0
            n = np.linalg.norm(out[i])
            if n:
                out[i] /= n
        return out
