"""JWT verification for tokens issued by the NestJS backend (HS256, shared secret).

There is no user table here: identity comes entirely from the verified token.
Nest payload: ``{id, name, email, iat, exp}`` (``sub`` is accepted instead of ``id``).
"""

from __future__ import annotations

from dataclasses import dataclass

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import Settings, get_settings
from .errors import AppError

_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class CurrentUser:
    id: str
    name: str
    email: str


def decode_token(token: str, settings: Settings) -> CurrentUser:
    """Verify signature + expiry and return the identity, or raise a 401 AppError."""
    if not settings.jwt_secret:
        raise AppError(500, "Server misconfigured: JWT_SECRET is not set.", "SERVER_MISCONFIGURED")
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["exp"]},
        )
    except jwt.ExpiredSignatureError:
        raise AppError(401, "Session expired. Please log in again.", "TOKEN_EXPIRED")
    except jwt.PyJWTError:
        raise AppError(401, "Invalid authentication token.", "INVALID_TOKEN")

    user_id = payload.get("id") or payload.get("sub")
    email = payload.get("email")
    if not user_id or not email:
        raise AppError(401, "Token is missing required identity claims.", "INVALID_TOKEN")
    return CurrentUser(id=str(user_id), name=str(payload.get("name") or ""), email=str(email))


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    settings: Settings = Depends(get_settings),
) -> CurrentUser:
    """FastAPI dependency: require a valid Bearer token."""
    if creds is None or creds.scheme.lower() != "bearer":
        raise AppError(401, "Authentication required.", "NOT_AUTHENTICATED")
    return decode_token(creds.credentials, settings)
