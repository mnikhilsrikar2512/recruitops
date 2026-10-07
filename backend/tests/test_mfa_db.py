"""Phase 3.6 against the real database: enrol, two-step sign-in, single-use
codes, recovery codes, disable with re-verify, Admins keep MFA, and the
company-activation gate (an Admin without MFA blocks a company going active)."""
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core import totp
from app.core.security import hash_password
from app.core.tokens import REFRESH_COOKIE
from app.db.session import create_db_engine
from app.main import create_application
from app.services.tenants import ActivationBlocked, activate_tenant

API = "/api/v1"
PASSWORD = "Mfa#Verification2026"


@pytest.fixture(scope="module")
def engine():
    try:
        engine = create_db_engine()
        with engine.connect() as connection:
            if connection.execute(text("SELECT OBJECT_ID(N'dbo.user_mfa')")).scalar() is None:
                pytest.skip("015_mfa.sql is not applied")
            if connection.execute(text("SELECT 1 FROM dbo.users WHERE email = N'ci.admin@recruitops-test.com'")).first() is None:
                pytest.skip("CI admin is not seeded")
        return engine
    except Exception:  # noqa: BLE001
        pytest.skip("Configured SQL Server database is not reachable")


def _user(engine, *, admin: bool, tenant_id: int | None = None) -> tuple[str, int]:
    email = f"mfa-{uuid.uuid4().hex[:8]}@example.com"
    with engine.begin() as connection:
        ci = connection.execute(
            text("SELECT TOP 1 location_id, tenant_id FROM dbo.users WHERE email = N'ci.admin@recruitops-test.com'")
        ).first()
        if admin:
            role = connection.execute(text("SELECT id FROM dbo.roles WHERE code = N'admin' AND tenant_id IS NULL")).scalar()
        else:  # a grant-less role: MFA is optional for it
            role = connection.execute(
                text("INSERT INTO dbo.roles (name, code, description, is_system_role, status, tenant_id) "
                     "OUTPUT INSERTED.id VALUES (:n, :c, N'mfa test', 0, N'active', :t)"),
                {"n": f"MFA {email[:12]}", "c": f"mfa-{email[4:12]}", "t": tenant_id or ci[1]},
            ).scalar_one()
        user_id = connection.execute(
            text("""INSERT INTO dbo.users (full_name, email, employee_code, password_hash, password_setup_status,
                     force_password_change_on_first_login, status, default_role_id, hierarchy_level, location_id, tenant_id)
                    OUTPUT INSERTED.id
                    VALUES (N'MFA Test', :e, :c, :h, N'active', 0, N'active', :r, N'L1', :l, :t)"""),
            {"e": email, "c": email[:20], "h": hash_password(PASSWORD), "r": role, "l": ci[0], "t": tenant_id or ci[1]},
        ).scalar_one()
    return email, int(user_id)


def _client() -> TestClient:
    return TestClient(create_application(), raise_server_exceptions=False)


def _sign_in(client: TestClient, email: str) -> dict:
    response = client.post(f"{API}/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200, response.text
    return response.json()


def _enroll(client: TestClient, headers: dict) -> tuple[str, list[str]]:
    started = client.post(f"{API}/auth/mfa/enroll", headers=headers)
    assert started.status_code == 200, started.text
    secret = started.json()["secret"]
    assert started.json()["otpauth_uri"].startswith("otpauth://totp/")
    verified = client.post(f"{API}/auth/mfa/verify", headers=headers,
                           json={"code": totp.code_at(secret, totp.current_step())})
    assert verified.status_code == 200, verified.text
    codes = verified.json()["recovery_codes"]
    assert len(codes) == 10
    return secret, codes


def test_two_step_sign_in_with_single_use_codes_and_recovery_codes(engine) -> None:
    email, _ = _user(engine, admin=False)
    client = _client()
    first = _sign_in(client, email)
    headers = {"Authorization": f"Bearer {first['token']}"}
    secret, recovery = _enroll(client, headers)

    challenge = _sign_in(client, email)
    assert challenge.get("mfa_required") is True and "token" not in challenge
    wrong = client.post(f"{API}/auth/mfa/challenge", json={"mfa_token": challenge["mfa_token"], "code": "000000"})
    assert wrong.status_code == 401
    code = totp.code_at(secret, totp.current_step() + 1)  # enrolment used the current step
    ok = client.post(f"{API}/auth/mfa/challenge", json={"mfa_token": challenge["mfa_token"], "code": code})
    assert ok.status_code == 200, ok.text
    assert ok.json()["token"] and ok.cookies.get(REFRESH_COOKIE)
    replay = client.post(f"{API}/auth/mfa/challenge", json={"mfa_token": _sign_in(client, email)["mfa_token"], "code": code})
    assert replay.status_code == 401  # a code works once

    via_recovery = client.post(f"{API}/auth/mfa/challenge",
                               json={"mfa_token": _sign_in(client, email)["mfa_token"], "recovery_code": recovery[0]})
    assert via_recovery.status_code == 200
    again = client.post(f"{API}/auth/mfa/challenge",
                        json={"mfa_token": _sign_in(client, email)["mfa_token"], "recovery_code": recovery[0]})
    assert again.status_code == 401  # recovery codes are single-use

    status = client.get(f"{API}/auth/mfa", headers={"Authorization": f"Bearer {via_recovery.json()['token']}"}).json()
    assert status["enabled"] is True and status["recovery_codes_remaining"] == 9


def test_disable_requires_a_code_and_admins_cannot_disable(engine) -> None:
    email, _ = _user(engine, admin=False)
    client = _client()
    headers = {"Authorization": f"Bearer {_sign_in(client, email)['token']}"}
    _secret, recovery = _enroll(client, headers)
    assert client.request("DELETE", f"{API}/auth/mfa", headers=headers, json={"code": "000000"}).status_code == 400
    assert client.request("DELETE", f"{API}/auth/mfa", headers=headers, json={"recovery_code": recovery[1]}).status_code == 204
    assert "token" in _sign_in(client, email)  # back to one step

    admin_email, _ = _user(engine, admin=True)
    admin_headers = {"Authorization": f"Bearer {_sign_in(client, admin_email)['token']}"}
    _secret, admin_recovery = _enroll(client, admin_headers)
    blocked = client.request("DELETE", f"{API}/auth/mfa", headers=admin_headers, json={"recovery_code": admin_recovery[0]})
    assert blocked.status_code == 403


def test_an_admin_without_mfa_blocks_a_company_from_going_active(engine) -> None:
    sfx = uuid.uuid4().hex[:8]
    with engine.begin() as connection:
        tenant_id = connection.execute(
            text("INSERT INTO dbo.tenants (slug, display_name, status) OUTPUT INSERTED.id VALUES (:s, :n, N'pending')"),
            {"s": f"mfa-gate-{sfx}", "n": f"MFA Gate {sfx}"},
        ).scalar_one()
    _email, admin_id = _user(engine, admin=True, tenant_id=int(tenant_id))
    with pytest.raises(ActivationBlocked):
        activate_tenant(engine, int(tenant_id))
    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO dbo.user_mfa (user_id, totp_secret, enabled_at) VALUES (:u, :s, SYSUTCDATETIME())"),
            {"u": admin_id, "s": totp.new_secret()},
        )
    activate_tenant(engine, int(tenant_id))
    with engine.connect() as connection:
        assert connection.execute(text("SELECT status FROM dbo.tenants WHERE id = :t"), {"t": tenant_id}).scalar() == "active"
