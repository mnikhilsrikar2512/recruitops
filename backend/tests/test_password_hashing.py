"""Password hashing upgrade: bcrypt as the default, legacy hash migration.

Covers:

1. New passwords hash with bcrypt (``$2b$`` prefix) — never stored unsalted.
2. ``verify_password`` still accepts legacy ``sha256:`` and ``pbkdf2$`` hashes.
3. ``needs_rehash`` flags exactly the non-bcrypt hashes.
4. Login with a legacy hash transparently upgrades it to bcrypt in the
   database (the real surface, DB-backed, skipped when SQL Server is down).

The historical bug this locks down: passwords were stored as unsalted
SHA-256 (``sha256:<hex>``), trivially crackable with rainbow tables.
"""
import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.security import (
    create_sha256_password_hash,
    hash_password,
    needs_rehash,
    verify_password,
)
from app.main import create_application


def test_hash_password_produces_bcrypt_hash() -> None:
    stored = hash_password("secret123")

    assert stored.startswith("$2")
    assert verify_password("secret123", stored)
    assert not verify_password("wrong", stored)


def test_bcrypt_hashes_are_salted() -> None:
    assert hash_password("same-password") != hash_password("same-password")


def test_verify_password_still_supports_legacy_hashes() -> None:
    legacy = create_sha256_password_hash("secret123")

    assert verify_password("secret123", legacy)
    assert not verify_password("wrong", legacy)


def test_needs_rehash_flags_only_non_bcrypt_hashes() -> None:
    assert needs_rehash(create_sha256_password_hash("x"))
    assert needs_rehash("pbkdf2$600000$ab$cd")
    assert not needs_rehash("")
    assert not needs_rehash(hash_password("x"))


def _db_reachable() -> bool:
    try:
        from sqlalchemy import text

        from app.db.session import create_db_engine

        engine = create_db_engine()
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


ADMIN_EMAIL_CANDIDATES = ["ci.admin@recruitops-test.com", "admin@executiveconnection.com"]
ADMIN_PASSWORD = "admin123"


@pytest.fixture(scope="module")
def client():
    if not _db_reachable():
        pytest.skip("Configured SQL Server database is not reachable")
    app = create_application()
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


def _login_admin(client: TestClient) -> tuple[str, dict]:
    last_error = None
    for email in ADMIN_EMAIL_CANDIDATES:
        response = client.post("/api/v1/auth/login", json={"email": email, "password": ADMIN_PASSWORD})
        if response.status_code == 200:
            body = response.json()
            return body["token"], body
        last_error = response.status_code
    pytest.fail(f"Seed admin login failed: {last_error}")


def _create_user_with_legacy_hash(client: TestClient, token: str, admin_user: dict) -> dict:
    """Admin creates a user, then forces their hash back to legacy sha256."""
    suffix = uuid.uuid4().hex[:8]
    payload = {
        "full_name": f"Legacy Hash {suffix}",
        "email": f"legacy-{suffix}@recruitops-test.com",
        "employee_code": f"LEG{suffix}",
        "primary_role_id": admin_user["primary_role"]["id"],
        "primary_location_id": admin_user["primary_location"]["id"],
        "status": "active",
    }
    response = client.post(
        "/api/v1/users/",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code in (200, 201), response.text
    created = response.json()
    user_id = created["id"] if "id" in created else created["user"]["id"]

    from sqlalchemy import text

    from app.db.session import create_db_engine

    engine = create_db_engine()
    with engine.begin() as connection:
        connection.execute(
            text("UPDATE dbo.users SET password_hash = :hash WHERE id = :user_id"),
            {"hash": create_sha256_password_hash("admin123"), "user_id": user_id},
        )
    return {"id": user_id, "email": payload["email"]}


def test_login_upgrades_legacy_hash_to_bcrypt(client: TestClient) -> None:
    token, admin_user = _login_admin(client)
    target = _create_user_with_legacy_hash(client, token, admin_user)

    from sqlalchemy import text

    from app.db.session import create_db_engine

    engine = create_db_engine()

    def stored_hash_prefix(user_id: int) -> str:
        with engine.connect() as connection:
            row = connection.execute(
                text("SELECT password_hash FROM dbo.users WHERE id = :user_id"),
                {"user_id": user_id},
            ).first()
        return str(row[0])[:7]

    assert stored_hash_prefix(target["id"]) == "sha256:", "test setup failed to plant legacy hash"

    # First login: legacy hash verifies, then migrates in place.
    login = client.post("/api/v1/auth/login", json={"email": target["email"], "password": "admin123"})
    assert login.status_code == 200, login.text
    assert stored_hash_prefix(target["id"]).startswith("$2b$"), "legacy hash was not upgraded on login"

    # Second login: bcrypt path verifies the migrated hash.
    again = client.post("/api/v1/auth/login", json={"email": target["email"], "password": "admin123"})
    assert again.status_code == 200

    # Wrong password is still rejected after migration.
    wrong = client.post("/api/v1/auth/login", json={"email": target["email"], "password": "nope"})
    assert wrong.status_code == 401
