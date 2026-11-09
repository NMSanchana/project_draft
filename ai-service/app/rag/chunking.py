"""Paragraph/sentence-aware chunking (~600-800 characters, ~100 overlap)."""

from __future__ import annotations

import re
from dataclasses import dataclass

TARGET = 750
HARD_MAX = 800
OVERLAP = 100
_SENT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(\[])")


@dataclass
class Chunk:
    text: str
    page: int
    chunk_id: int


def _sentences(page_text: str) -> list[str]:
    out: list[str] = []
    for para in re.split(r"\n\s*\n", page_text):
        para = re.sub(r"[ \t]+", " ", para.replace("\r", "")).strip()
        para = re.sub(r"\s*\n\s*", " ", para)
        if not para:
            continue
        for s in _SENT.split(para):
            s = s.strip()
            while len(s) > HARD_MAX:  # a single very long sentence: split at a space
                cut = s.rfind(" ", 0, HARD_MAX) or HARD_MAX
                out.append(s[:cut].strip())
                s = s[cut:].strip()
            if s:
                out.append(s)
    return out


def chunk_pages(pages: list[tuple[int, str]]) -> list[Chunk]:
    """Pack sentences into chunks of about 750 characters; each chunk starts with ~100 chars of the previous one.

    ``pages`` is ``[(page_number, text), ...]``; chunks never span pages (so citations stay exact).
    """
    chunks: list[Chunk] = []
    for page, text in pages:
        sents, cur = _sentences(text), []
        size = 0
        for s in sents:
            if cur and size + len(s) + 1 > TARGET:
                chunks.append(Chunk(" ".join(cur), page, len(chunks)))
                tail, acc = [], 0
                for prev in reversed(cur):  # carry back sentences until ~OVERLAP chars
                    if acc >= OVERLAP:
                        break
                    if len(prev) > 2 * OVERLAP + 50:  # a very long sentence: carry only its trailing words
                        part = prev[-OVERLAP:]
                        part = part[part.find(" ") + 1 :] if " " in part else part
                        tail.insert(0, part)
                        acc += len(part) + 1
                        break
                    tail.insert(0, prev)
                    acc += len(prev) + 1
                cur, size = tail, acc
                if size + len(s) + 1 > HARD_MAX:  # never let the overlap push a chunk past the hard limit
                    cur, size = [], 0
            cur.append(s)
            size += len(s) + 1
        if cur and (not chunks or chunks[-1].page != page or " ".join(cur) != chunks[-1].text):
            chunks.append(Chunk(" ".join(cur), page, len(chunks)))
    return [c for c in chunks if c.text.strip()]
