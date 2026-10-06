"""Access tokens (JWT) and refresh tokens (opaque) — Phase 3.1/3.2.

Access token: HS256 JWT, short TTL, claims ``sub`` (user id), ``tenant_id``,
``sid`` (session = refresh-token family), ``typ='access'``. The API still
checks the session row on every request, so revocation is immediate.

Refresh token: 48 random bytes, sent only in an HttpOnly cookie, stored as a
SHA-256 hash, single use (rotation on every refresh).
"""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import DEV_JWT_SIGNING_KEY, settings
from app.core.security import sha256_hex

ALGORITHM = "HS256"
ACCESS_TYPE = "access"
REFRESH_COOKIE = "ro_refresh"
REFRESH_COOKIE_PATH = "/api/v1/auth"


class InvalidToken(Exception):
    """Signature, expiry, type or shape is wrong."""


def _signing_key() -> str:
    return settings.jwt_signing_key or DEV_JWT_SIGNING_KEY


def issue_access_token(*, user_id: int, tenant_id: int | None, session_id: int) -> tuple[str, datetime]:
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=settings.jwt_access_ttl_minutes)
    claims = {
        "sub": str(user_id),
        "tenant_id": tenant_id,
        "sid": session_id,
        "typ": ACCESS_TYPE,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    return jwt.encode(claims, _signing_key(), algorithm=ALGORITHM), expires_at


def decode_access_token(token: str) -> dict:
    try:
        claims = jwt.decode(
            token, _signing_key(), algorithms=[ALGORITHM], options={"require": ["exp", "sub", "sid", "typ"]}
        )
    except jwt.PyJWTError as exc:
        raise InvalidToken(str(exc)) from exc
    if claims.get("typ") != ACCESS_TYPE:
        raise InvalidToken("not an access token")
    return claims


def looks_like_jwt(token: str) -> bool:
    return token.count(".") == 2


def new_refresh_token() -> tuple[str, str]:
    """(raw token for the cookie, hash for the database)."""
    raw = secrets.token_urlsafe(48)
    return raw, sha256_hex(raw)


def hash_refresh_token(raw: str) -> str:
    return sha256_hex(raw)
