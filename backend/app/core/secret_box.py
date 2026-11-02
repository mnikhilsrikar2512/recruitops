"""Encryption at rest for small secrets (Phase 6.3), first used for TOTP
seeds in ``dbo.user_mfa``.

AES-256-GCM with a key ring:

    MFA_ENCRYPTION_KEYS="2026b:<base64 32 bytes>,2026a:<base64 32 bytes>"

The first key encrypts; every listed key can decrypt, so a rotation is:
add the new key first, deploy, run ``scripts/encrypt_mfa_secrets.py`` to
re-wrap every row, then drop the old key. Each value is bound to its row
(the "context", e.g. ``user_mfa:42``), so a ciphertext copied onto another
user's row doesn't decrypt.

Stored format: ``enc:v1:<key id>:<base64url(nonce || ciphertext+tag)>``.
A value without the prefix is a legacy plaintext seed; it is still read so
the switch-over needs no downtime, and the re-wrap script encrypts it.

Generate a key:  python -c "import os,base64;print(base64.urlsafe_b64encode(os.urandom(32)).decode())"
"""
from __future__ import annotations

import base64
import hashlib
import os

from app.core.config import settings

PREFIX = "enc:v1:"
DEV_KEY_ID = "dev"
_DEV_KEY = hashlib.sha256(b"recruitops-dev-only-mfa-key-not-for-production").digest()


class SecretBoxError(ValueError):
    pass


def _b64decode(value: str) -> bytes:
    value = value.strip()
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def parse_key_ring(raw: str) -> list[tuple[str, bytes]]:
    """``id:key,id:key`` → [(id, 32-byte key)], first = current."""
    ring: list[tuple[str, bytes]] = []
    for part in (raw or "").split(","):
        part = part.strip()
        if not part:
            continue
        key_id, sep, encoded = part.partition(":")
        if not sep or not key_id or ":" in key_id:
            raise SecretBoxError("each key must look like <id>:<base64 key>")
        try:
            key = _b64decode(encoded)
        except Exception as exc:
            raise SecretBoxError(f"key {key_id!r} is not valid base64") from exc
        if len(key) != 32:
            raise SecretBoxError(f"key {key_id!r} must be 32 bytes (AES-256), got {len(key)}")
        if any(existing == key_id for existing, _ in ring):
            raise SecretBoxError(f"key id {key_id!r} is listed twice")
        ring.append((key_id, key))
    return ring


def key_ring() -> list[tuple[str, bytes]]:
    ring = parse_key_ring(settings.mfa_encryption_keys)
    if ring:
        return ring
    if settings.is_production:  # validate_settings() stops this boot earlier
        raise SecretBoxError("MFA_ENCRYPTION_KEYS is required in staging/production")
    return [(DEV_KEY_ID, _DEV_KEY)]


def current_key_id() -> str:
    return key_ring()[0][0]


def is_encrypted(value: str | None) -> bool:
    return bool(value) and value.startswith(PREFIX)


def encrypt(plaintext: str, context: str) -> str:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    key_id, key = key_ring()[0]
    nonce = os.urandom(12)
    sealed = AESGCM(key).encrypt(nonce, plaintext.encode("utf-8"), context.encode("utf-8"))
    return f"{PREFIX}{key_id}:{base64.urlsafe_b64encode(nonce + sealed).decode().rstrip('=')}"


def decrypt(stored: str, context: str) -> str:
    if not is_encrypted(stored):
        return stored  # legacy plaintext, re-wrapped by scripts/encrypt_mfa_secrets.py
    from cryptography.exceptions import InvalidTag
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    key_id, _, payload = stored[len(PREFIX):].partition(":")
    keys = dict(key_ring())
    if key_id not in keys:
        raise SecretBoxError(f"no key {key_id!r} in MFA_ENCRYPTION_KEYS (was it removed before re-wrapping?)")
    blob = _b64decode(payload)
    try:
        return AESGCM(keys[key_id]).decrypt(blob[:12], blob[12:], context.encode("utf-8")).decode("utf-8")
    except InvalidTag as exc:
        raise SecretBoxError("secret failed authentication (wrong row, wrong key, or tampered)") from exc


def needs_rewrap(stored: str) -> bool:
    """Plaintext, or encrypted under a key that is no longer the current one."""
    if not is_encrypted(stored):
        return True
    return stored[len(PREFIX):].partition(":")[0] != current_key_id()


def mfa_context(user_id: int) -> str:
    return f"user_mfa:{int(user_id)}"
