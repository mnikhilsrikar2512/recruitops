"""Setup checklist (frontend cleanup F.1) — a new company's admin sees what
is left to set up, worked out from the company's data, and can hide it.

Runs against the configured database (skipped when unreachable).
"""
from __future__ import annotations

from sqlalchemy import text

from tests.test_metric_buckets_db import _engine, client  # noqa: F401  (fixtures)
from tests.test_signup_db import PASSWORD, _company, _email, _signup, created  # noqa: F401  (fixtures)


def _new_company_admin(client, created, monkeypatch) -> tuple[dict, dict]:
    from app.core.config import settings

    monkeypatch.setattr(settings, "mfa_enforce_admin_enrollment_setting", False)
    email = _email()
    created.append(email)
    token = _signup(client, email).json()["dev_verify_token"]
    assert client.post("/api/v1/signup/verify", json={"token": token}).status_code == 200
    login = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['token']}"}, _company(email)


def test_new_company_sees_checklist_worked_out_from_its_data(client, created, monkeypatch):
    headers, company = _new_company_admin(client, created, monkeypatch)
    response = client.get("/api/v1/settings/setup-checklist", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    items = {i["key"]: i for i in body["items"]}
    assert set(items) == {"offices", "team", "stages", "client", "requisition"}
    assert body["dismissed"] is False and body["complete"] is False
    assert not items["offices"]["done"] and not items["team"]["done"] and not items["requisition"]["done"]
    assert items["offices"]["optional"] and items["client"]["optional"] and not items["team"]["optional"]

    # A second office ticks "offices" — nothing is ticked by hand.
    with _engine().begin() as connection:
        connection.execute(text(
            "INSERT INTO dbo.branches (name, code, location, status, offers_enabled, tenant_id) "
            "VALUES (N'Second Office', :code, N'Pune', N'active', 1, :t)"),
            {"code": f"SO{company['id']}", "t": company["id"]})
    items = {i["key"]: i for i in client.get("/api/v1/settings/setup-checklist", headers=headers).json()["items"]}
    assert items["offices"]["done"]


def test_checklist_can_be_hidden_and_brought_back(client, created, monkeypatch):
    headers, _ = _new_company_admin(client, created, monkeypatch)
    hidden = client.put("/api/v1/settings/setup-checklist/dismissed", json={"dismissed": True}, headers=headers)
    assert hidden.status_code == 200 and hidden.json()["dismissed"] is True
    shown = client.put("/api/v1/settings/setup-checklist/dismissed", json={"dismissed": False}, headers=headers)
    assert shown.json()["dismissed"] is False


def test_checklist_needs_sign_in(client):
    assert client.get("/api/v1/settings/setup-checklist").status_code == 401
