"""F01: password hashing and JWT access-token helpers.

Kept framework-agnostic (no FastAPI imports) so it can be unit tested in
isolation and swapped later without touching the request layer.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt

from app.core.config import settings

_JWT_SUBJECT_CLAIM = "sub"
_JWT_ROLE_CLAIM = "role"


def hash_password(plain_password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(plain_password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except ValueError:
        # Malformed hash: never treat as a match.
        return False


def create_access_token(*, user_id: str, role: str, expires_minutes: int | None = None) -> str:
    expire_delta = timedelta(
        minutes=expires_minutes
        if expires_minutes is not None
        else settings.access_token_expire_minutes
    )
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        _JWT_SUBJECT_CLAIM: user_id,
        _JWT_ROLE_CLAIM: role,
        "iat": now,
        "exp": now + expire_delta,
    }
    return jwt.encode(payload, settings.app_secret_key, algorithm=settings.jwt_algorithm)


class InvalidTokenError(Exception):
    """Raised when a bearer token is missing, expired, or malformed."""


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.app_secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as exc:
        raise InvalidTokenError(str(exc)) from exc
