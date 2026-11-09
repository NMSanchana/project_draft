"""Filesystem layout for uploads and cleaned frames (per user, per dataset)."""

from __future__ import annotations

import hashlib
import re
import shutil
from pathlib import Path

import pandas as pd

from .config import get_settings


def safe_id(value: str) -> str:
    """Make an id safe to use as a path component."""
    if re.fullmatch(r"[A-Za-z0-9_-]{1,64}", value):
        return value
    return hashlib.sha256(value.encode()).hexdigest()[:32]


def dataset_dir(user_id: str, dataset_id: str) -> Path:
    return get_settings().upload_path / safe_id(user_id) / safe_id(dataset_id)


def save_dataset_files(user_id: str, dataset_id: str, original: bytes, file_name: str, clean_df: pd.DataFrame) -> None:
    d = dataset_dir(user_id, dataset_id)
    d.mkdir(parents=True, exist_ok=True)
    (d / file_name).write_bytes(original)
    clean_df.to_parquet(d / "clean.parquet", index=False)


def load_clean_frame(user_id: str, dataset_id: str) -> pd.DataFrame:
    path = dataset_dir(user_id, dataset_id) / "clean.parquet"
    if not path.exists():
        raise FileNotFoundError(f"Cleaned data for dataset {dataset_id} is missing.")
    return pd.read_parquet(path)


def delete_dataset_files(user_id: str, dataset_id: str) -> None:
    shutil.rmtree(dataset_dir(user_id, dataset_id), ignore_errors=True)
