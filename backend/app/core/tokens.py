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


MFA_TYPE = "mfa"
MFA_TOKEN_MINUTES = 5


def issue_mfa_token(*, user_id: int, email: str) -> tuple[str, datetime]:
    """Proof that the password was right; only exchangeable at
    /auth/mfa/challenge together with a valid code, within 5 minutes."""
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=MFA_TOKEN_MINUTES)
    claims = {"sub": str(user_id), "email": email, "typ": MFA_TYPE,
              "iat": int(now.timestamp()), "exp": int(expires_at.timestamp())}
    return jwt.encode(claims, _signing_key(), algorithm=ALGORITHM), expires_at


def decode_mfa_token(token: str) -> dict:
    try:
        claims = jwt.decode(token, _signing_key(), algorithms=[ALGORITHM], options={"require": ["exp", "sub", "typ"]})
    except jwt.PyJWTError as exc:
        raise InvalidToken(str(exc)) from exc
    if claims.get("typ") != MFA_TYPE:
        raise InvalidToken("not an MFA token")
    return claims


# ---- Phase 5.2: signup setup token ---------------------------------------
SIGNUP_TYPE = "signup"
SIGNUP_TOKEN_MINUTES = 30


def issue_signup_token(*, user_id: int, tenant_id: int) -> tuple[str, datetime]:
    """After the email link is used: lets the new admin set up two-step
    verification (the company isn't active yet, so there is no session)."""
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=SIGNUP_TOKEN_MINUTES)
    claims = {"sub": str(user_id), "tid": str(tenant_id), "typ": SIGNUP_TYPE,
              "iat": int(now.timestamp()), "exp": int(expires_at.timestamp())}
    return jwt.encode(claims, _signing_key(), algorithm=ALGORITHM), expires_at


def decode_signup_token(token: str) -> dict:
    try:
        claims = jwt.decode(token, _signing_key(), algorithms=[ALGORITHM], options={"require": ["exp", "sub", "tid", "typ"]})
    except jwt.PyJWTError as exc:
        raise InvalidToken(str(exc)) from exc
    if claims.get("typ") != SIGNUP_TYPE:
        raise InvalidToken("not a signup token")
    return claims
