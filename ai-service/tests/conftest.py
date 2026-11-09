"""Test fixtures: isolated settings, temp SQLite + upload dir, token factory."""

from __future__ import annotations

import os
import time
from pathlib import Path

import jwt
import pytest

SECRET = "test-secret-shared-with-nest"
ROOT = Path(__file__).resolve().parents[2]
SAMPLE_DIR = ROOT / "sample-data"


@pytest.fixture(scope="session", autouse=True)
def _env(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("ai")
    os.environ.update(
        JWT_SECRET=SECRET,
        DATABASE_URL=f"sqlite:///{tmp / 'test.db'}",
        UPLOAD_DIR=str(tmp / "uploads"),
        KB_DIR=str(tmp / "kb"),
        QDRANT_URL="http://127.0.0.1:9",  # unreachable on purpose
        OLLAMA_URL="http://127.0.0.1:9",
        MAX_UPLOAD_MB="1",
        KB_AUTOSYNC="false",
    )
    from app.config import get_settings

    get_settings.cache_clear()
    yield


@pytest.fixture()
def client(_env):
    from fastapi.testclient import TestClient

    from app.db import init_db, init_engine
    from app.main import create_app

    init_engine()
    init_db()
    with TestClient(create_app()) as c:
        yield c


def make_token(
    user_id="665f1c2a9b1e8a0012345678",
    email="a@example.com",
    name="Alice",
    secret=SECRET,
    exp_in=3600,
    extra=None,
    alg="HS256",
    use_sub=False,
) -> str:
    now = int(time.time())
    payload = {"name": name, "email": email, "iat": now, "exp": now + exp_in}
    payload["sub" if use_sub else "id"] = user_id
    payload.update(extra or {})
    payload = {k: v for k, v in payload.items() if v is not None}
    return jwt.encode(payload, secret, algorithm=alg)


def auth(token: str | None = None, **kw) -> dict:
    return {"Authorization": f"Bearer {token or make_token(**kw)}"}
