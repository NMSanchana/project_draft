"""Safe CSV ingestion: encoding + delimiter detection, header normalisation, filename sanitising."""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass, field
from pathlib import PurePath

import pandas as pd


class DataError(ValueError):
    """The uploaded data cannot be analysed. The message is shown to the user (HTTP 422)."""


@dataclass
class IngestResult:
    df: pd.DataFrame  # every column is a string; typing happens in clean.py
    encoding: str
    delimiter: str
    warnings: list[str] = field(default_factory=list)


def sanitize_filename(name: str | None) -> str:
    """Strip any path, keep only ``[A-Za-z0-9._-]`` and force a ``.csv`` extension."""
    base = PurePath((name or "upload.csv").replace("\\", "/")).name
    base = re.sub(r"[^A-Za-z0-9._-]+", "_", base).strip("._") or "upload"
    stem = base[:-4] if base.lower().endswith(".csv") else base
    stem = stem.strip("._") or "upload"
    return f"{stem[:100]}.csv"


def decode_bytes(raw: bytes) -> tuple[str, str]:
    """Try utf-8-sig, utf-8, then cp1252, finally latin-1 (which never fails)."""
    for enc in ("utf-8-sig", "utf-8", "cp1252"):
        try:
            return raw.decode(enc), enc
        except UnicodeDecodeError:
            continue
    return raw.decode("latin-1"), "latin-1"


def sniff_delimiter(text: str) -> str:
    sample = text[:20000]
    try:
        return csv.Sniffer().sniff(sample, delimiters=",;\t|").delimiter
    except csv.Error:
        first = sample.splitlines()[0] if sample.splitlines() else ""
        counts = {d: first.count(d) for d in ",;\t|"}
        best = max(counts, key=counts.get)
        return best if counts[best] > 0 else ","


def normalise_headers(cols: list[str]) -> list[str]:
    """Trim, collapse whitespace, fill blanks and de-duplicate header names."""
    seen: dict[str, int] = {}
    out: list[str] = []
    for i, c in enumerate(cols):
        name = re.sub(r"\s+", " ", str(c).replace("\ufeff", "")).strip() or f"column_{i + 1}"
        seen[name] = seen.get(name, 0) + 1
        out.append(name if seen[name] == 1 else f"{name}_{seen[name]}")
    return out


def read_csv_bytes(raw: bytes) -> IngestResult:
    """Parse raw bytes into an all-string DataFrame, or raise :class:`DataError`."""
    if not raw or not raw.strip():
        raise DataError("The uploaded file is empty.")
    if b"\x00" in raw[:4096]:
        raise DataError("The file looks binary, not a text CSV. Please export your data as CSV.")
    text, enc = decode_bytes(raw)
    delim = sniff_delimiter(text)
    try:
        df = pd.read_csv(
            io.StringIO(text),
            sep=delim,
            dtype=str,
            skipinitialspace=True,
            on_bad_lines="skip",
            engine="python" if len(delim) != 1 else "c",
        )
    except (pd.errors.ParserError, pd.errors.EmptyDataError) as exc:
        raise DataError(f"The file could not be parsed as CSV: {exc}") from exc

    warnings: list[str] = []
    df.columns = normalise_headers(list(df.columns))
    unnamed_empty = [c for c in df.columns if c.lower().startswith("unnamed") and df[c].isna().all()]
    df = df.drop(columns=unnamed_empty).dropna(how="all")
    for c in df.columns:  # trim stray whitespace in text cells
        df[c] = df[c].str.strip().replace({"": None})
    if df.shape[1] < 2:
        raise DataError("Only one column was found. The file may use an unusual delimiter or is not a table of sales records.")
    if df.empty:
        raise DataError("The CSV has headers but no data rows.")
    if enc not in ("utf-8", "utf-8-sig"):
        warnings.append(f"File was not UTF-8; decoded as {enc}.")
    return IngestResult(df=df.reset_index(drop=True), encoding=enc, delimiter=delim, warnings=warnings)
