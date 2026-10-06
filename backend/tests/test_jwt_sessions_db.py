"""Phase 3.1–3.4 exit-gate tests against the real database.

- Login returns a short-lived JWT and sets the refresh token as an HttpOnly cookie.
- Refresh rotates the refresh token; the new access token works.
- Refresh-theft: re-using a rotated refresh token kills the whole sign-in.
- An expired refresh token requires a full re-login.
- Pre-JWT opaque tokens answer 401 (one-release cutover, D-08).
- Logout ends the sign-in; password change ends every OTHER sign-in.
- Sessions: list mine, sign out others.
"""
import uuid

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.security import generate_session_token, hash_session_token
from app.core.tokens import REFRESH_COOKIE
from app.db.session import create_db_engine
from app.main import create_application

API = "/api/v1"
ADMIN = ("ci.admin@recruitops-test.com", "admin123")


@pytest.fixture(scope="module")
def engine():
    try:
        engine = create_db_engine()
        with engine.connect() as connection:
            if connection.execute(text("SELECT OBJECT_ID(N'dbo.user_refresh_tokens')")).scalar() is None:
                pytest.skip("013_jwt_sessions.sql is not applied")
            if connection.execute(text("SELECT 1 FROM dbo.users WHERE email = :e"), {"e": ADMIN[0]}).first() is None:
                pytest.skip("CI admin is not seeded")
        return engine
    except Exception:  # noqa: BLE001
        pytest.skip("Configured SQL Server database is not reachable")


def _login(email: str = ADMIN[0], password: str = ADMIN[1]) -> tuple[TestClient, dict, str]:
    client = TestClient(create_application(), raise_server_exceptions=False)
    response = client.post(f"{API}/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    refresh = response.cookies.get(REFRESH_COOKIE)
    assert refresh, "refresh cookie missing"
    return client, {"Authorization": f"Bearer {response.json()['token']}"}, refresh


def _refresh(client: TestClient, refresh: str):
    client.cookies.clear()
    return client.post(f"{API}/auth/refresh", cookies={REFRESH_COOKIE: refresh})


def test_login_issues_jwt_and_httponly_refresh_cookie(engine) -> None:
    client = TestClient(create_application(), raise_server_exceptions=False)
    response = client.post(f"{API}/auth/login", json={"email": ADMIN[0], "password": ADMIN[1]})
    assert response.status_code == 200
    claims = jwt.decode(response.json()["token"], options={"verify_signature": False})
    assert claims["typ"] == "access" and claims["sid"] and claims["sub"] and "tenant_id" in claims
    cookie_header = response.headers.get("set-cookie", "")
    assert REFRESH_COOKIE in cookie_header
    assert "httponly" in cookie_header.lower() and "samesite=strict" in cookie_header.lower()
    assert REFRESH_COOKIE not in response.text  # never in the body


def test_refresh_rotates_and_new_access_token_works(engine) -> None:
    client, _headers, refresh = _login()
    response = _refresh(client, refresh)
    assert response.status_code == 200, response.text
    new_refresh = response.cookies.get(REFRESH_COOKIE)
    assert new_refresh and new_refresh != refresh
    me = client.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {response.json()['token']}"})
    assert me.status_code == 200


def test_reusing_a_rotated_refresh_token_kills_the_whole_family(engine) -> None:
    client, _headers, first = _login()
    rotated = _refresh(client, first)
    assert rotated.status_code == 200
    second = rotated.cookies.get(REFRESH_COOKIE)
    newest_access = {"Authorization": f"Bearer {rotated.json()['token']}"}

    replay = _refresh(client, first)  # the stolen, already-used token
    assert replay.status_code == 401

    assert _refresh(client, second).status_code == 401  # the legitimate chain is dead too
    assert client.get(f"{API}/auth/me", headers=newest_access).status_code == 401


def test_expired_refresh_requires_full_login(engine) -> None:
    client, _headers, refresh = _login()
    with engine.begin() as connection:
        connection.execute(
            text("UPDATE dbo.user_refresh_tokens SET expires_at = DATEADD(MINUTE, -1, SYSUTCDATETIME()) "
                 "WHERE token_hash = :h"),
            {"h": hash_session_token(refresh)},
        )
    assert _refresh(client, refresh).status_code == 401


def test_old_opaque_tokens_are_refused(engine) -> None:
    raw = generate_session_token()
    with engine.begin() as connection:
        user_id = connection.execute(text("SELECT id FROM dbo.users WHERE email = :e"), {"e": ADMIN[0]}).scalar_one()
        connection.execute(
            text("INSERT INTO dbo.user_sessions (user_id, session_token_hash, expires_at, auth_kind) "
                 "VALUES (:u, :h, DATEADD(HOUR, 1, SYSUTCDATETIME()), N'opaque')"),
            {"u": user_id, "h": hash_session_token(raw)},
        )
    client = TestClient(create_application(), raise_server_exceptions=False)
    assert client.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {raw}"}).status_code == 401


def test_tampered_access_token_is_refused(engine) -> None:
    client, headers, _refresh_token = _login()
    token = headers["Authorization"].split()[1]
    head, body, sig = token.split(".")
    forged = f"{head}.{body}.{sig[:-2]}{'AA' if not sig.endswith('AA') else 'BB'}"
    assert client.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {forged}"}).status_code == 401


def test_logout_ends_access_and_refresh(engine) -> None:
    client, headers, refresh = _login()
    assert client.post(f"{API}/auth/logout", headers=headers).status_code == 200
    assert client.get(f"{API}/auth/me", headers=headers).status_code == 401
    assert _refresh(client, refresh).status_code == 401


def _dedicated_user(engine, password: str) -> str:
    """A throwaway user, so signing out "other" sessions can't touch the
    CI admin's sessions that other test modules hold."""
    from app.core.security import hash_password

    sfx = uuid.uuid4().hex[:8]
    email = f"jwt-{sfx}@example.com"
    with engine.begin() as connection:
        row = connection.execute(
            text("SELECT TOP 1 default_role_id, location_id, tenant_id FROM dbo.users WHERE email = :e"), {"e": ADMIN[0]}
        ).first()
        connection.execute(
            text("""INSERT INTO dbo.users (full_name, email, employee_code, password_hash, password_setup_status,
                     force_password_change_on_first_login, status, default_role_id, hierarchy_level, location_id, tenant_id)
                    VALUES (N'JWT Test', :e, :c, :h, N'active', 0, N'active', :r, N'L1', :l, :t)"""),
            {"e": email, "c": f"JWT-{sfx}", "h": hash_password(password), "r": row[0], "l": row[1], "t": row[2]},
        )
    return email


def test_sessions_list_and_sign_out_others(engine) -> None:
    email = _dedicated_user(engine, "Sessions#Test2026")
    client_a, headers_a, _ = _login(email, "Sessions#Test2026")
    client_b, headers_b, refresh_b = _login(email, "Sessions#Test2026")
    listed = client_a.get(f"{API}/auth/sessions", headers=headers_a)
    assert listed.status_code == 200
    items = listed.json()["items"]
    assert sum(1 for item in items if item["current"]) == 1
    revoked = client_a.delete(f"{API}/auth/sessions", headers=headers_a)
    assert revoked.status_code == 200 and revoked.json()["revoked"] >= 1
    assert client_b.get(f"{API}/auth/me", headers=headers_b).status_code == 401
    assert _refresh(client_b, refresh_b).status_code == 401
    assert client_a.get(f"{API}/auth/me", headers=headers_a).status_code == 200


def test_password_change_ends_other_sign_ins(engine) -> None:
    old, new = "Old#Password2026", "New#Password2026x"
    email = _dedicated_user(engine, old)
    client_a, headers_a, _ = _login(email, old)
    client_b, headers_b, refresh_b = _login(email, old)
    changed = client_a.post(f"{API}/auth/password/change", headers=headers_a,
                            json={"current_password": old, "new_password": new})
    assert changed.status_code == 200, changed.text
    assert client_a.get(f"{API}/auth/me", headers=headers_a).status_code == 200
    assert client_b.get(f"{API}/auth/me", headers=headers_b).status_code == 401
    assert _refresh(client_b, refresh_b).status_code == 401
