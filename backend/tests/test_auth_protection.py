"""Phase 3 exit gate: password policy (3.5), lockout (3.5), rate limits (3.7),
perimeter headers and CORS (3.8)."""
import uuid

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import text

from app.core import rate_limit
from app.core.config import settings
from app.core.password_policy import password_problem
from app.main import create_application
from app.schemas.auth import PasswordChangeRequest, PasswordResetRequest

API = "/api/v1"


# ---- 3.5 password policy -----------------------------------------------------

def test_eight_character_password_is_rejected() -> None:
    assert password_problem("Abc12345") is not None
    with pytest.raises(ValidationError):
        PasswordChangeRequest(current_password="x", new_password="Abc12345")


@pytest.mark.parametrize("password", ["password1234", "Password2024!!", "qwerty123456", "iloveyou!!!!", "111111111111"])
def test_common_or_breached_passwords_are_rejected(password: str) -> None:
    assert password_problem(password) is not None
    with pytest.raises(ValidationError):
        PasswordResetRequest(token="t", new_password=password)


def test_long_uncommon_passphrase_is_accepted() -> None:
    assert password_problem("correct horse battery staple") is None
    assert password_problem("Tq7#vLm2!pZx9w") is None


# ---- 3.7 rate limits -----------------------------------------------------------

@pytest.fixture
def limits_on(monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    # Simulate sitting behind one trusted reverse proxy (the real staging/
    # production topology -- see app/core/net.py) so these tests can still
    # vary the caller's IP via X-Forwarded-For. Without this, the header is
    # untrusted by default and every request here would share one bucket
    # (the TestClient's fixed direct-peer address).
    monkeypatch.setattr(settings, "trusted_proxy_count", 1)
    rate_limit.reset_rate_limits()
    yield
    rate_limit.reset_rate_limits()


def _fake_login(*_args, **_kwargs):
    raise HTTPException(status_code=401, detail="Invalid email or password")


def test_login_is_limited_to_5_per_minute_per_ip(limits_on, monkeypatch) -> None:
    monkeypatch.setattr("app.api.v1.auth.login_service", _fake_login)
    client = TestClient(create_application(), raise_server_exceptions=False)
    codes = [client.post(f"{API}/auth/login", json={"email": f"user{n}@example.com", "password": "x"}).status_code
             for n in range(6)]
    assert codes[:5] == [401] * 5 and codes[5] == 429
    blocked = client.post(f"{API}/auth/login", json={"email": "another@example.com", "password": "x"})
    assert blocked.status_code == 429 and blocked.headers.get("retry-after")


def test_login_is_limited_to_10_per_minute_per_account(limits_on, monkeypatch) -> None:
    monkeypatch.setattr("app.api.v1.auth.login_service", _fake_login)
    client = TestClient(create_application(), raise_server_exceptions=False)
    codes = [
        client.post(f"{API}/auth/login", json={"email": "victim@example.com", "password": "x"},
                    headers={"X-Forwarded-For": f"10.0.0.{n}"}).status_code
        for n in range(11)
    ]
    assert codes[:10] == [401] * 10 and codes[10] == 429


def test_forgot_password_is_limited_per_account(limits_on, monkeypatch) -> None:
    monkeypatch.setattr("app.api.v1.auth.forgot_password_service",
                        lambda engine, payload: {"message": "If an account with that email exists, a reset link has been sent"})
    client = TestClient(create_application(), raise_server_exceptions=False)
    codes = [
        client.post(f"{API}/auth/password/forgot", json={"email": "victim@example.com"},
                    headers={"X-Forwarded-For": f"10.1.0.{n}"}).status_code
        for n in range(4)
    ]
    assert codes[:3] == [200] * 3 and codes[3] == 429


# ---- 3.7b client-IP spoofing (X-Forwarded-For trust boundary) -----------------

def test_spoofed_forwarded_for_is_ignored_with_no_trusted_proxy(limits_on, monkeypatch) -> None:
    """Without a configured trusted proxy (the default), a client setting
    its own X-Forwarded-For must not get a fresh rate-limit bucket per
    request -- that would make the login IP limit meaningless."""
    monkeypatch.setattr(settings, "trusted_proxy_count", 0)
    monkeypatch.setattr("app.api.v1.auth.login_service", _fake_login)
    client = TestClient(create_application(), raise_server_exceptions=False)
    codes = [
        client.post(f"{API}/auth/login", json={"email": f"user{n}@example.com", "password": "x"},
                    headers={"X-Forwarded-For": f"203.0.113.{n}"}).status_code
        for n in range(6)
    ]
    # Every request lands in the same (direct-peer) bucket despite the
    # forged header claiming a different IP each time.
    assert codes[:5] == [401] * 5 and codes[5] == 429


def test_trusted_proxy_hop_is_used_not_the_client_supplied_prefix(limits_on) -> None:
    """With one trusted proxy configured, the IP used for rate limiting is
    the entry that proxy appended (the real client, as far as our own
    infrastructure can vouch for) -- never anything the client prepended
    onto the header itself."""
    from starlette.requests import Request

    scope = {
        "type": "http",
        "headers": [(b"x-forwarded-for", b"9.9.9.9, 203.0.113.55")],
        "client": ("10.0.0.1", 12345),
    }
    request = Request(scope)
    assert rate_limit.client_ip(request) == "203.0.113.55"


# ---- 3.8 perimeter -------------------------------------------------------------

def test_security_headers_are_set() -> None:
    response = TestClient(create_application()).get(f"{API}/health")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert "default-src 'none'" in response.headers["content-security-policy"]
    assert response.headers["referrer-policy"] == "no-referrer"


def test_cors_rejects_a_disallowed_origin_and_allows_an_allowlisted_one() -> None:
    client = TestClient(create_application())
    preflight = {"Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "content-type"}
    evil = client.options(f"{API}/auth/login", headers={"Origin": "https://evil.example.com", **preflight})
    assert "access-control-allow-origin" not in {k.lower() for k in evil.headers}
    allowed_origin = settings.cors_origin_list()[0]
    good = client.options(f"{API}/auth/login", headers={"Origin": allowed_origin, **preflight})
    assert good.headers.get("access-control-allow-origin") == allowed_origin
    assert good.headers.get("access-control-allow-credentials") == "true"


# ---- 3.5 lockout (database) ------------------------------------------------------

def test_account_locks_after_five_wrong_passwords() -> None:
    from app.core.security import hash_password
    from app.db.session import create_db_engine

    try:
        engine = create_db_engine()
        with engine.connect() as connection:
            if connection.execute(text("SELECT COL_LENGTH(N'dbo.users', N'locked_until')")).scalar() is None:
                pytest.skip("014_login_lockout.sql is not applied")
            admin = connection.execute(
                text("SELECT TOP 1 default_role_id, location_id, tenant_id FROM dbo.users WHERE email = N'ci.admin@recruitops-test.com'")
            ).first()
    except Exception:  # noqa: BLE001
        pytest.skip("Configured SQL Server database is not reachable")
    if admin is None:
        pytest.skip("CI admin is not seeded")
    email, good = f"lockout-{uuid.uuid4().hex[:8]}@example.com", "Lockout#Test2026"
    with engine.begin() as connection:
        connection.execute(
            text("""INSERT INTO dbo.users (full_name, email, employee_code, password_hash, password_setup_status,
                     force_password_change_on_first_login, status, default_role_id, hierarchy_level, location_id, tenant_id)
                    VALUES (N'Lockout', :e, :c, :h, N'active', 0, N'active', :r, N'L1', :l, :t)"""),
            {"e": email, "c": email[:20], "h": hash_password(good), "r": admin[0], "l": admin[1], "t": admin[2]},
        )
    client = TestClient(create_application(), raise_server_exceptions=False)
    wrong = [client.post(f"{API}/auth/login", json={"email": email, "password": "Wrong#Password2026"}).status_code
             for _ in range(5)]
    assert wrong == [401] * 5
    locked = client.post(f"{API}/auth/login", json={"email": email, "password": good})
    assert locked.status_code == 429  # even the right password waits out the lock
    with engine.begin() as connection:
        connection.execute(text("UPDATE dbo.users SET locked_until = DATEADD(MINUTE, -1, SYSUTCDATETIME()) WHERE email = :e"),
                           {"e": email})
    assert client.post(f"{API}/auth/login", json={"email": email, "password": good}).status_code == 200
