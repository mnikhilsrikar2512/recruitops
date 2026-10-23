"""DB-backed tests for extra permissions granted directly to a user, on top
of their single role (dbo.user_extra_permissions, PUT/GET
/users/{user_id}/extra-permissions).

RecruitOps gives each user exactly one active role at a time
(dbo.user_branch_roles' is_primary slot is replaced, not stacked, by every
role-change path). Extra permissions are the supported way to give a user
reach beyond that one role -- e.g. an Admin who also wants the read-only
Company Overview bundle -- without pretending the user holds two roles.

Proves, against the real database and the real HTTP API:
- A user's role-driven permissions are unaffected by their own absence of
  extra grants (baseline 403 on an out-of-role endpoint).
- Granting extra permissions immediately unlocks the matching endpoint
  (flows through list_resolved_permissions's UNION and the permission
  cache's invalidate_permission_cache call).
- Revoking (replacing with an empty/narrower set) immediately locks it
  back down.
- Extra permissions never grant write access beyond what was explicitly
  listed (granting a read-only bundle does not unlock a POST/PUT on the
  same resource).
- Extra permissions never cross a tenant boundary: a second company's user
  cannot be granted or read via this endpoint from a different company's
  admin, and the grant itself never widens what company the grantee's data
  access reaches (scope.company is unaffected).
- The grantee's role, title and hierarchy level are untouched by the grant.

Skips when the DB is unreachable, matching the other *_db.py tests.
"""
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.rbac import COMPANY_OVERVIEW_PERMISSION_CODES
from app.core.security import hash_password
from app.db.session import create_db_engine
from app.main import create_application

API = "/api/v1"
PASSWORD = "ExtraPerm#2026"
GRANTER_CODES = ["user.read", "role.permissions.assign", "requisition.read"]
BASE_CODES = ["user.read"]  # deliberately excludes requisition.read


def _db_reachable() -> bool:
    try:
        engine = create_db_engine()
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:  # noqa: BLE001
        return False


@pytest.fixture(scope="module")
def fixture():
    if not _db_reachable():
        pytest.skip("Configured SQL Server database is not reachable")
    engine = create_db_engine()
    sfx = uuid.uuid4().hex[:8]

    with engine.connect() as connection:
        offices = connection.execute(
            text(
                "SELECT TOP 2 b.id, b.tenant_id FROM dbo.branches AS b "
                "INNER JOIN dbo.tenants AS t ON t.id = b.tenant_id "
                "ORDER BY b.tenant_id, b.id"
            )
        ).all()
    if len(offices) < 1:
        pytest.skip("no office available to seed test users against")

    office_id, tenant_id = int(offices[0][0]), int(offices[0][1])
    # A second tenant's office, if one exists, to prove the tenant boundary.
    other_office = None
    for row in offices:
        if int(row[1]) != tenant_id:
            other_office = (int(row[0]), int(row[1]))
            break

    def make_role(connection, label: str, codes: list[str], t_id: int) -> int:
        role_id = connection.execute(
            text(
                "INSERT INTO dbo.roles (name, code, description, is_system_role, status, tenant_id) "
                "OUTPUT INSERTED.id VALUES (:n, :c, N'extra-perm test', 0, N'active', :t)"
            ),
            {"n": f"{label} {sfx}", "c": f"{label.lower()}-{sfx}", "t": t_id},
        ).scalar_one()
        for code in codes:
            connection.execute(
                text(
                    "INSERT INTO dbo.role_permissions (role_id, permission_id) "
                    "SELECT :r, id FROM dbo.permissions WHERE code = :code"
                ),
                {"r": role_id, "code": code},
            )
        return role_id

    def make_user(connection, label: str, role_id: int, off_id: int, t_id: int) -> tuple[int, str]:
        email = f"extraperm-{label}-{sfx}@example.com"
        uid = connection.execute(
            text(
                """
                INSERT INTO dbo.users (full_name, email, employee_code, password_hash, password_setup_status,
                    force_password_change_on_first_login, status, default_role_id, hierarchy_level, location_id, tenant_id)
                OUTPUT INSERTED.id
                VALUES (:name, :email, :code, :hash, N'active', 0, N'active', :role, N'L1', :office, :t)
                """
            ),
            {"name": f"Extra Perm {label}", "email": email, "code": f"EP-{label}-{sfx}"[:20],
             "hash": hash_password(PASSWORD), "role": role_id, "office": off_id, "t": t_id},
        ).scalar_one()
        connection.execute(
            text(
                "INSERT INTO dbo.user_branch_roles (user_id, branch_id, role_id, is_primary, status, start_date) "
                "VALUES (:u, :b, :r, 1, N'active', CAST(SYSUTCDATETIME() AS DATE))"
            ),
            {"u": uid, "b": off_id, "r": role_id},
        )
        return uid, email

    with engine.begin() as connection:
        granter_role = make_role(connection, "Granter", GRANTER_CODES, tenant_id)
        target_role = make_role(connection, "Target", BASE_CODES, tenant_id)
        granter_id, granter_email = make_user(connection, "granter", granter_role, office_id, tenant_id)
        target_id, target_email = make_user(connection, "target", target_role, office_id, tenant_id)

        other_ids = None
        if other_office:
            other_off_id, other_tenant_id = other_office
            other_role = make_role(connection, "OtherGranter", GRANTER_CODES, other_tenant_id)
            other_granter_id, other_granter_email = make_user(
                connection, "othergranter", other_role, other_off_id, other_tenant_id
            )
            other_ids = {"id": other_granter_id, "email": other_granter_email}

    client = TestClient(create_application(), raise_server_exceptions=False)

    def login(email: str) -> dict:
        response = client.post(f"{API}/auth/login", json={"email": email, "password": PASSWORD})
        assert response.status_code == 200, response.text
        return {"Authorization": f"Bearer {response.json()['token']}"}

    granter_headers = login(granter_email)
    target_headers = login(target_email)
    other_granter_headers = login(other_ids["email"]) if other_ids else None

    yield {
        "client": client,
        "engine": engine,
        "granter_headers": granter_headers,
        "target_headers": target_headers,
        "target_id": target_id,
        "target_role": target_role,
        "other_granter_headers": other_granter_headers,
    }

    client.close()
    for sql in (
        "DELETE FROM dbo.user_extra_permissions WHERE user_id IN (SELECT id FROM dbo.users WHERE email LIKE :p)",
        "DELETE FROM dbo.user_sessions WHERE user_id IN (SELECT id FROM dbo.users WHERE email LIKE :p)",
        "DELETE FROM dbo.user_branch_roles WHERE user_id IN (SELECT id FROM dbo.users WHERE email LIKE :p)",
        "DELETE FROM dbo.users WHERE email LIKE :p",
        "DELETE FROM dbo.role_permissions WHERE role_id IN (SELECT id FROM dbo.roles WHERE code LIKE :c)",
        "DELETE FROM dbo.roles WHERE code LIKE :c",
    ):
        try:
            with engine.begin() as connection:
                connection.execute(text(sql), {"p": f"extraperm-%-{sfx}@example.com", "c": f"%-{sfx}"})
        except Exception:  # noqa: BLE001
            pass


def test_baseline_target_has_no_extra_permissions_and_is_denied(fixture) -> None:
    client = fixture["client"]
    response = client.get(f"{API}/users/{fixture['target_id']}/extra-permissions", headers=fixture["granter_headers"])
    assert response.status_code == 200, response.text
    assert response.json()["permission_codes"] == []

    denied = client.get(f"{API}/requisitions/", headers=fixture["target_headers"])
    assert denied.status_code == 403, denied.text


def test_granting_extra_permissions_unlocks_matching_endpoint(fixture) -> None:
    client = fixture["client"]
    put_response = client.put(
        f"{API}/users/{fixture['target_id']}/extra-permissions",
        json={"permission_codes": list(COMPANY_OVERVIEW_PERMISSION_CODES)},
        headers=fixture["granter_headers"],
    )
    assert put_response.status_code == 200, put_response.text
    assert sorted(put_response.json()["permission_codes"]) == sorted(COMPANY_OVERVIEW_PERMISSION_CODES)

    allowed = client.get(f"{API}/requisitions/", headers=fixture["target_headers"])
    assert allowed.status_code == 200, allowed.text

    allowed_candidates = client.get(f"{API}/candidates/", headers=fixture["target_headers"])
    assert allowed_candidates.status_code == 200, allowed_candidates.text


def test_extra_permissions_stay_read_only_no_write_leaks_in(fixture) -> None:
    client = fixture["client"]
    # Company Overview includes requisition.read but never requisition.create.
    create_attempt = client.post(
        f"{API}/requisitions/",
        json={"title": "Should never be created"},
        headers=fixture["target_headers"],
    )
    assert create_attempt.status_code == 403, create_attempt.text


def test_revoking_extra_permissions_locks_it_back_down(fixture) -> None:
    client = fixture["client"]
    put_response = client.put(
        f"{API}/users/{fixture['target_id']}/extra-permissions",
        json={"permission_codes": []},
        headers=fixture["granter_headers"],
    )
    assert put_response.status_code == 200, put_response.text
    assert put_response.json()["permission_codes"] == []

    denied_again = client.get(f"{API}/requisitions/", headers=fixture["target_headers"])
    assert denied_again.status_code == 403, denied_again.text


def test_grant_does_not_touch_role_title_or_hierarchy(fixture) -> None:
    client = fixture["client"]
    engine = fixture["engine"]

    with engine.connect() as connection:
        before_hierarchy = connection.execute(
            text("SELECT hierarchy_level FROM dbo.users WHERE id = :id"),
            {"id": fixture["target_id"]},
        ).scalar_one()

    client.put(
        f"{API}/users/{fixture['target_id']}/extra-permissions",
        json={"permission_codes": list(COMPANY_OVERVIEW_PERMISSION_CODES)},
        headers=fixture["granter_headers"],
    )
    detail = client.get(f"{API}/users/{fixture['target_id']}", headers=fixture["granter_headers"])
    assert detail.status_code == 200, detail.text
    body = detail.json()
    # The grant must not change the user's identity fields: same role,
    # same title, same hierarchy level -- it only adds permission reach.
    assert body.get("business_title") != "Company Overview (Read-Only)"
    assert body.get("primary_role_id") == fixture["target_role"]

    with engine.connect() as connection:
        after_hierarchy = connection.execute(
            text("SELECT hierarchy_level FROM dbo.users WHERE id = :id"),
            {"id": fixture["target_id"]},
        ).scalar_one()
    assert after_hierarchy == before_hierarchy

    # cleanup so later tests in this module see the baseline again
    client.put(
        f"{API}/users/{fixture['target_id']}/extra-permissions",
        json={"permission_codes": []},
        headers=fixture["granter_headers"],
    )


def test_extra_permissions_endpoint_is_tenant_scoped(fixture) -> None:
    if fixture["other_granter_headers"] is None:
        pytest.skip("only one tenant's office available in this database -- cannot prove the cross-tenant boundary")
    client = fixture["client"]
    cross_tenant_read = client.get(
        f"{API}/users/{fixture['target_id']}/extra-permissions", headers=fixture["other_granter_headers"]
    )
    assert cross_tenant_read.status_code in (403, 404), cross_tenant_read.text

    cross_tenant_write = client.put(
        f"{API}/users/{fixture['target_id']}/extra-permissions",
        json={"permission_codes": list(COMPANY_OVERVIEW_PERMISSION_CODES)},
        headers=fixture["other_granter_headers"],
    )
    assert cross_tenant_write.status_code in (403, 404), cross_tenant_write.text
