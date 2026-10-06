"""Access-token encode/verify rules (Phase 3.1) — no database."""
import time

import jwt
import pytest

from app.core import tokens


def test_issue_and_decode_round_trip() -> None:
    token, expires_at = tokens.issue_access_token(user_id=7, tenant_id=3, session_id=11)
    claims = tokens.decode_access_token(token)
    assert claims["sub"] == "7" and claims["tenant_id"] == 3 and claims["sid"] == 11
    assert expires_at.timestamp() > time.time()


def test_expired_token_is_rejected(monkeypatch) -> None:
    monkeypatch.setattr(tokens.settings, "jwt_access_ttl_minutes", -1)
    token, _ = tokens.issue_access_token(user_id=7, tenant_id=3, session_id=11)
    with pytest.raises(tokens.InvalidToken):
        tokens.decode_access_token(token)


def test_wrong_key_and_wrong_type_are_rejected() -> None:
    foreign = jwt.encode({"sub": "7", "sid": 1, "typ": "access", "exp": int(time.time()) + 60}, "another-key-of-sufficient-length-000000", algorithm="HS256")
    with pytest.raises(tokens.InvalidToken):
        tokens.decode_access_token(foreign)
    refresh_like = jwt.encode({"sub": "7", "sid": 1, "typ": "refresh", "exp": int(time.time()) + 60}, tokens._signing_key(), algorithm="HS256")
    with pytest.raises(tokens.InvalidToken):
        tokens.decode_access_token(refresh_like)


def test_none_algorithm_is_rejected() -> None:
    unsigned = jwt.encode({"sub": "7", "sid": 1, "typ": "access", "exp": int(time.time()) + 60}, None, algorithm="none")
    with pytest.raises(tokens.InvalidToken):
        tokens.decode_access_token(unsigned)


def test_refresh_tokens_are_random_and_hashed() -> None:
    raw_a, hash_a = tokens.new_refresh_token()
    raw_b, hash_b = tokens.new_refresh_token()
    assert raw_a != raw_b and hash_a != raw_a and tokens.hash_refresh_token(raw_a) == hash_a
