from app.core.security import create_sha256_password_hash, hash_session_token, verify_password


def test_verify_password_supports_sha256_hashes() -> None:
    stored_hash = create_sha256_password_hash("secret123")

    assert verify_password("secret123", stored_hash) is True
    assert verify_password("wrong", stored_hash) is False


def test_hash_session_token_is_deterministic() -> None:
    assert hash_session_token("abc") == hash_session_token("abc")
    assert hash_session_token("abc") != hash_session_token("xyz")
