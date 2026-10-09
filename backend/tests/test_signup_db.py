"""Phase 5.2 exit gate — a company goes from nothing to an active,
MFA-protected admin through self-serve signup, with the legal versions
recorded; and the ops provisioning path builds the same company.

Runs against the configured database (skipped when unreachable). Every
company it creates is purged afterwards.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from app.core import rate_limit
from app.core.totp import code_at, current_step
from tests.test_metric_buckets_db import _engine, client  # noqa: F401  (fixtures)

PASSWORD = "Signup-Gate-Strong-Pass-2026!"


def _versions(client) -> dict[str, int]:
    return {d["doc_type"]: d["version"] for d in client.get("/api/v1/legal/documents").json()["items"]}


def _email() -> str:
    return f"signup.{uuid.uuid4().hex[:10]}@recruitops-test.com"


@pytest.fixture()
def created(client):
    rate_limit.reset_rate_limits()
    emails: list[str] = []
    yield emails
    from app.services.tenant_purge import purge_company

    engine = _engine()
    for email in emails:
        with engine.connect() as connection:
            tenant = connection.execute(text("SELECT tenant_id FROM dbo.users WHERE email = :e"), {"e": email}).scalar()
        if tenant is None:
            continue
        purge_company(engine, int(tenant), 0, hold_days=1)
        with engine.begin() as connection:
            connection.execute(text("DELETE FROM dbo.privacy_audit_hold WHERE tenant_id = :t"), {"t": tenant})
            connection.execute(text("DELETE FROM dbo.tenants WHERE id = :t"), {"t": tenant})
    rate_limit.reset_rate_limits()


def _signup(client, email, **extra):
    body = {"company_name": "Signup Gate Co", "admin_name": "Gate Admin", "email": email, "password": PASSWORD,
            "city": "Pune", "accepted": _versions(client), **extra}
    return client.post("/api/v1/signup/", json=body)


def _company(email):
    with _engine().connect() as connection:
        return connection.execute(text(
            "SELECT t.id, t.status, t.onboarding, u.id AS user_id, u.email_verified_at FROM dbo.users u "
            "JOIN dbo.tenants t ON t.id = u.tenant_id WHERE u.email = :e"), {"e": email}).mappings().first()


def test_signup_needs_current_legal_versions_and_strong_password(client, created):
    email = _email()
    stale = _signup(client, email, accepted={"tos": 0, "privacy": 0, "dpa": 0})
    assert stale.status_code == 422
    weak = client.post("/api/v1/signup/", json={"company_name": "X Co", "admin_name": "X", "email": email,
                                                "password": "password", "accepted": _versions(client)})
    assert weak.status_code == 422
    bot = _signup(client, email, website="http://spam.example")
    assert bot.status_code == 202 and _company(email) is None


def test_signup_verify_mfa_activate_then_sign_in(client, created, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "mfa_enforce_admin_enrollment_setting", True)
    email = _email()
    created.append(email)
    response = _signup(client, email)
    assert response.status_code == 202, response.text
    token = response.json()["dev_verify_token"]
    company = _company(email)
    assert company["status"] == "pending" and company["onboarding"] == "self_serve" and company["email_verified_at"] is None

    # Pending company: no sign-in yet.
    assert client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD}).status_code == 403
    # Same email again: same generic answer, no second company.
    again = _signup(client, email)
    assert again.status_code == 202 and again.json().get("dev_verify_token") is None

    with _engine().connect() as connection:
        accepted = connection.execute(text(
            "SELECT doc_type, on_behalf_of_company FROM dbo.legal_acceptances WHERE user_id = :u ORDER BY doc_type"),
            {"u": company["user_id"]}).all()
    assert [(a[0], bool(a[1])) for a in accepted] == [("dpa", True), ("privacy", False), ("tos", False)]

    assert client.post("/api/v1/signup/verify", json={"token": "x" * 40}).status_code == 400
    verified = client.post("/api/v1/signup/verify", json={"token": token})
    assert verified.status_code == 200, verified.text
    assert verified.json()["next"] == "mfa"
    setup = verified.json()["setup_token"]
    assert client.post("/api/v1/signup/verify", json={"token": token}).status_code == 400  # one use

    started = client.post("/api/v1/signup/mfa/start", json={"setup_token": setup})
    assert started.status_code == 200, started.text
    bad = client.post("/api/v1/signup/mfa/confirm", json={"setup_token": setup, "code": "000000"})
    assert bad.status_code in (400, 409)
    code = code_at(started.json()["secret"], current_step())
    confirmed = client.post("/api/v1/signup/mfa/confirm", json={"setup_token": setup, "code": code})
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["company_status"] == "active" and len(confirmed.json()["recovery_codes"]) >= 8
    assert _company(email)["status"] == "active" and _company(email)["email_verified_at"] is not None

    login = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert login.status_code == 200, login.text
    assert login.json().get("mfa_token")  # admin signs in with the second factor


def test_without_mfa_enforcement_verify_activates(client, created, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "mfa_enforce_admin_enrollment_setting", False)
    email = _email()
    created.append(email)
    token = _signup(client, email).json()["dev_verify_token"]
    resent = client.post("/api/v1/signup/resend", json={"email": email})
    assert resent.status_code == 202
    new_token = resent.json()["dev_verify_token"]
    assert new_token and new_token != token
    assert client.post("/api/v1/signup/verify", json={"token": token}).status_code == 400  # replaced by the resend
    verified = client.post("/api/v1/signup/verify", json={"token": new_token})
    assert verified.json() == {"next": "login", "company_status": "active", "setup_token": None}
    login = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert login.status_code == 200 and login.json().get("token")


def test_ops_provisioning_builds_the_same_company(client, created):
    from app.core.security import hash_password
    from app.services.provisioning import EmailTaken, provision_company

    email = _email()
    created.append(email)
    result = provision_company(_engine(), company_name="Ops Gate Co", admin_name="Ops Admin", admin_email=email, city=None,
                               password_hash=hash_password("unused-" + uuid.uuid4().hex), password_ready=False,
                               onboarding="ops", email_verified=False)
    with _engine().connect() as connection:
        row = connection.execute(text(
            "SELECT t.status, t.onboarding, b.id AS branch, l.id AS location, u.password_setup_status, r.code AS role "
            "FROM dbo.tenants t JOIN dbo.branches b ON b.tenant_id = t.id JOIN dbo.locations l ON l.id = b.id "
            "JOIN dbo.users u ON u.tenant_id = t.id JOIN dbo.roles r ON r.id = u.default_role_id WHERE t.id = :t"),
            {"t": result["tenant_id"]}).mappings().one()
        profile = connection.execute(text("SELECT COUNT(*) FROM dbo.company_entities WHERE tenant_id = :t AND is_primary = 1"),
                                     {"t": result["tenant_id"]}).scalar_one()
    assert row["status"] == "pending" and row["onboarding"] == "ops" and row["branch"] == row["location"]
    assert row["password_setup_status"] == "reset-required" and row["role"] == "admin" and profile == 1
    with pytest.raises(EmailTaken):
        provision_company(_engine(), company_name="Dup", admin_name="Dup", admin_email=email, city=None,
                          password_hash="x", password_ready=False, onboarding="ops", email_verified=False)


def test_ops_admin_sets_password_then_mfa_then_active(client, created, monkeypatch):
    from datetime import datetime, timedelta, timezone

    from app.core.config import settings
    from app.core.security import generate_session_token, hash_password, hash_session_token
    from app.repositories.users import create_password_reset_token
    from app.services.provisioning import provision_company

    monkeypatch.setattr(settings, "mfa_enforce_admin_enrollment_setting", True)
    email = _email()
    created.append(email)
    result = provision_company(_engine(), company_name="Ops Flow Co", admin_name="Ops Flow", admin_email=email, city=None,
                               password_hash=hash_password("unused-" + uuid.uuid4().hex), password_ready=False,
                               onboarding="ops", email_verified=False)
    token = generate_session_token()
    create_password_reset_token(_engine(), user_id=result["admin_id"], token_hash=hash_session_token(token), purpose="admin-reset",
                                issued_by_user_id=None, expires_at=datetime.now(timezone.utc) + timedelta(hours=1))
    setup = client.post("/api/v1/auth/password/setup", json={"token": token, "new_password": PASSWORD})
    assert setup.status_code == 200, setup.text
    assert setup.json()["next"] == "mfa" and setup.json()["setup_token"]
    assert _company(email)["email_verified_at"] is not None
    started = client.post("/api/v1/signup/mfa/start", json={"setup_token": setup.json()["setup_token"]})
    code = code_at(started.json()["secret"], current_step())
    confirmed = client.post("/api/v1/signup/mfa/confirm", json={"setup_token": setup.json()["setup_token"], "code": code})
    assert confirmed.status_code == 200 and confirmed.json()["company_status"] == "active"
