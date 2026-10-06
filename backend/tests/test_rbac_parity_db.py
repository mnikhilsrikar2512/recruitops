"""Plan 2.9 parity harness: two users with IDENTICAL grants in the same
office see identical API results (RBAC spec §2.1). Access depends on grants
and office, never on who the user is — except the deliberately personal
surfaces (own candidates, own notifications), which are excluded.

Runs against the real database; skips when it is unreachable.
"""
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.security import hash_password
from app.db.session import create_db_engine
from app.main import create_application

API = "/api/v1"
PASSWORD = "Parity#2026"
RECRUITER_CODES = [
    "requisition.read", "client.read", "client.contact.read", "pipeline.read.summary", "pipeline.read.detail",
    "interview.read", "offer.read", "meeting.read", "daily_update.read", "approval.read",
    "notification.read", "dashboard.read_my_work", "location.read",
]
# Office- or company-scoped lists: results must not depend on the user.
SHARED_LISTS = [
    "/requisitions/?page_size=100", "/clients/?page_size=100", "/approvals/?page_size=100",
    "/meetings/?page_size=100", "/daily-updates/?page_size=100", "/interviews/?page_size=100",
    "/offers/?page_size=100", "/locations/?page_size=100", "/pipeline/board",
    "/users/?page_size=100", "/roles/?page_size=100",
]


@pytest.fixture(scope="module")
def pair():
    try:
        engine = create_db_engine()
        with engine.connect() as connection:
            office = connection.execute(
                text("SELECT TOP 1 b.id, b.tenant_id FROM dbo.branches AS b "
                     "INNER JOIN dbo.tenants AS t ON t.id = b.tenant_id WHERE t.slug = N'default' ORDER BY b.id")
            ).first()
    except Exception:  # noqa: BLE001
        pytest.skip("Configured SQL Server database is not reachable")
    if office is None:
        pytest.skip("no default company office")
    office_id, tenant_id = int(office[0]), int(office[1])
    sfx = uuid.uuid4().hex[:8]
    with engine.begin() as connection:
        role_id = connection.execute(
            text("INSERT INTO dbo.roles (name, code, description, is_system_role, status, tenant_id) "
                 "OUTPUT INSERTED.id VALUES (:n, :c, N'parity', 0, N'active', :t)"),
            {"n": f"Parity {sfx}", "c": f"parity-{sfx}", "t": tenant_id},
        ).scalar_one()
        for code in RECRUITER_CODES:
            connection.execute(
                text("INSERT INTO dbo.role_permissions (role_id, permission_id) SELECT :r, id FROM dbo.permissions WHERE code = :code"),
                {"r": role_id, "code": code},
            )
        users = []
        for n in (1, 2):
            email = f"parity-{n}-{sfx}@example.com"
            uid = connection.execute(
                text("""
                    INSERT INTO dbo.users (full_name, email, employee_code, password_hash, password_setup_status,
                        force_password_change_on_first_login, status, default_role_id, hierarchy_level, location_id, tenant_id)
                    OUTPUT INSERTED.id
                    VALUES (:name, :email, :code, :hash, N'active', 0, N'active', :role, N'L1', :office, :t)
                """),
                {"name": f"Parity User {n}", "email": email, "code": f"PAR{n}-{sfx}", "hash": hash_password(PASSWORD),
                 "role": role_id, "office": office_id, "t": tenant_id},
            ).scalar_one()
            connection.execute(
                text("INSERT INTO dbo.user_branch_roles (user_id, branch_id, role_id, is_primary, status, start_date) "
                     "VALUES (:u, :b, :r, 1, N'active', CAST(SYSUTCDATETIME() AS DATE))"),
                {"u": uid, "b": office_id, "r": role_id},
            )
            users.append(email)
    client = TestClient(create_application(), raise_server_exceptions=False)
    headers = []
    for email in users:
        response = client.post(f"{API}/auth/login", json={"email": email, "password": PASSWORD})
        assert response.status_code == 200, response.text
        headers.append({"Authorization": f"Bearer {response.json()['token']}"})
    yield client, headers
    client.close()
    for sql in (
        "DELETE FROM dbo.user_sessions WHERE user_id IN (SELECT id FROM dbo.users WHERE email LIKE :p)",
        "DELETE FROM dbo.user_branch_roles WHERE user_id IN (SELECT id FROM dbo.users WHERE email LIKE :p)",
        "DELETE FROM dbo.users WHERE email LIKE :p",
        "DELETE FROM dbo.role_permissions WHERE role_id IN (SELECT id FROM dbo.roles WHERE code = :c)",
        "DELETE FROM dbo.roles WHERE code = :c",
    ):
        try:
            with engine.begin() as connection:
                connection.execute(text(sql), {"p": f"parity-%-{sfx}@example.com", "c": f"parity-{sfx}"})
        except Exception:  # noqa: BLE001
            pass


def _shape(response):
    body = response.json() if response.content else None
    if isinstance(body, dict) and "items" in body:
        return response.status_code, sorted(str(item.get("id")) for item in body["items"])
    if isinstance(body, list):
        return response.status_code, sorted(str(item.get("id") or item.get("application_id")) for item in body)
    return response.status_code, None


@pytest.mark.parametrize("path", SHARED_LISTS)
def test_identical_grants_identical_results(pair, path) -> None:
    client, (first, second) = pair
    assert _shape(client.get(f"{API}{path}", headers=first)) == _shape(client.get(f"{API}{path}", headers=second)), path


def test_identical_grants_identical_permissions_and_pages(pair) -> None:
    client, (first, second) = pair
    a = client.get(f"{API}/permissions/me", headers=first).json()
    b = client.get(f"{API}/permissions/me", headers=second).json()
    assert sorted(a["permissions"]) == sorted(b["permissions"])
    assert a.get("allowed_pages") == b.get("allowed_pages")
    assert a.get("scopes") == b.get("scopes")
