"""Company (tenant) isolation — Phase 2.3 regression, against the real DB.

Decision D-04 / Q5 (docs/decisions-2026-10-06.md): a company admin sees
every office of their OWN company and nothing of any other company.

Builds a second company ("B") next to the seed admin's company ("A") with
its own office and its own company admin, then proves through the HTTP API
that neither admin can list, read, or reference the other company's data.
Skips when the database is unreachable or 010_tenants.sql is not applied.
"""
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.security import hash_password
from app.db.session import create_db_engine
from app.main import create_application

ADMIN_EMAILS = ["ci.admin@recruitops-test.com", "admin@executiveconnection.com"]
ADMIN_PASSWORD = "admin123"
B_PASSWORD = "CompanyB#2026"
API = "/api/v1"


def _engine_or_skip():
    try:
        engine = create_db_engine()
        with engine.connect() as connection:
            if connection.execute(text("SELECT OBJECT_ID(N'dbo.tenants')")).scalar() is None:
                pytest.skip("010_tenants.sql is not applied")
        return engine
    except Exception:  # noqa: BLE001
        pytest.skip("Configured SQL Server database is not reachable")


def _login(client: TestClient, email: str, password: str) -> dict[str, str] | None:
    response = client.post(f"{API}/auth/login", json={"email": email, "password": password})
    if response.status_code != 200:
        return None
    return {"Authorization": f"Bearer {response.json()['token']}"}


@pytest.fixture(scope="module")
def world():
    engine = _engine_or_skip()
    app = create_application()
    client = TestClient(app, raise_server_exceptions=False)

    headers_a = None
    email_a = None
    for email in ADMIN_EMAILS:
        headers_a = _login(client, email, ADMIN_PASSWORD)
        if headers_a:
            email_a = email
            break
    if headers_a is None:
        pytest.skip("Seed admin login failed; seed users first")

    sfx = uuid.uuid4().hex[:8]
    with engine.begin() as connection:
        row = connection.execute(
            text("SELECT id, tenant_id FROM dbo.users WHERE email = :email"), {"email": email_a}
        ).mappings().one()
        tenant_a, admin_a_id = int(row["tenant_id"]), int(row["id"])
        office_a = connection.execute(
            text("SELECT TOP 1 id FROM dbo.branches WHERE tenant_id = :t ORDER BY id"), {"t": tenant_a}
        ).scalar_one()
        admin_role = connection.execute(
            text("SELECT id FROM dbo.roles WHERE code = N'admin' AND tenant_id IS NULL")
        ).scalar_one()
        tenant_b = connection.execute(
            text(
                "INSERT INTO dbo.tenants (slug, display_name, status) OUTPUT INSERTED.id "
                "VALUES (:slug, :name, N'active')"
            ),
            {"slug": f"company-b-{sfx}", "name": f"Company B {sfx}"},
        ).scalar_one()
        # Same office code as company A's first office is allowed (per-company codes).
        code_a = connection.execute(text("SELECT code FROM dbo.branches WHERE id = :id"), {"id": office_a}).scalar_one()
        office_b = connection.execute(
            text(
                "INSERT INTO dbo.branches (name, code, location, status, offers_enabled, tenant_id) "
                "OUTPUT INSERTED.id VALUES (:name, :code, :name, N'active', 1, :t)"
            ),
            {"name": f"Company B HQ {sfx}", "code": code_a, "t": tenant_b},
        ).scalar_one()
        connection.execute(
            text(
                """
                SET IDENTITY_INSERT dbo.locations ON;
                INSERT INTO dbo.locations (id, name, code, location, status, tenant_id)
                VALUES (:id, :name, :code, :name, N'active', :t);
                SET IDENTITY_INSERT dbo.locations OFF;
                """
            ),
            {"id": office_b, "name": f"Company B HQ {sfx}", "code": code_a, "t": tenant_b},
        )
        email_b = f"admin-b-{sfx}@example.com"
        admin_b_id = connection.execute(
            text(
                """
                INSERT INTO dbo.users (
                    full_name, email, employee_code, password_hash, password_setup_status,
                    force_password_change_on_first_login, status,
                    default_role_id, hierarchy_level, location_id, tenant_id
                )
                OUTPUT INSERTED.id
                VALUES (N'Company B Admin', :email, :code, :hash, N'active', 0, N'active', :role, N'L5', :office, :t)
                """
            ),
            {"email": email_b, "code": f"ADMB-{sfx}", "hash": hash_password(B_PASSWORD), "role": admin_role, "office": office_b, "t": tenant_b},
        ).scalar_one()
        connection.execute(
            text(
                "INSERT INTO dbo.user_branch_roles (user_id, branch_id, role_id, is_primary, status, start_date) "
                "VALUES (:u, :b, :r, 1, N'active', CAST(SYSUTCDATETIME() AS DATE))"
            ),
            {"u": admin_b_id, "b": office_b, "r": admin_role},
        )
        # A company-B recruiter-manager with an execution role (every code),
        # because the company admin is control-plane only (D-03).
        exec_role = connection.execute(
            text(
                "INSERT INTO dbo.roles (name, code, description, is_system_role, status, tenant_id) "
                "OUTPUT INSERTED.id VALUES (:name, :code, N'test', 0, N'active', :t)"
            ),
            {"name": f"B Full {sfx}", "code": f"b-full-{sfx}", "t": tenant_b},
        ).scalar_one()
        connection.execute(
            text("INSERT INTO dbo.role_permissions (role_id, permission_id) SELECT :r, id FROM dbo.permissions"),
            {"r": exec_role},
        )
        email_exec_b = f"exec-b-{sfx}@example.com"
        exec_b_id = connection.execute(
            text(
                """
                INSERT INTO dbo.users (
                    full_name, email, employee_code, password_hash, password_setup_status,
                    force_password_change_on_first_login, status,
                    default_role_id, hierarchy_level, location_id, tenant_id
                )
                OUTPUT INSERTED.id
                VALUES (N'Company B Exec', :email, :code, :hash, N'active', 0, N'active', :role, N'L3', :office, :t)
                """
            ),
            {"email": email_exec_b, "code": f"EXB-{sfx}", "hash": hash_password(B_PASSWORD), "role": exec_role,
             "office": office_b, "t": tenant_b},
        ).scalar_one()
        connection.execute(
            text(
                "INSERT INTO dbo.user_branch_roles (user_id, branch_id, role_id, is_primary, status, start_date) "
                "VALUES (:u, :b, :r, 1, N'active', CAST(SYSUTCDATETIME() AS DATE))"
            ),
            {"u": exec_b_id, "b": office_b, "r": exec_role},
        )
        client_b = connection.execute(
            text(
                "INSERT INTO dbo.client_companies (branch_id, name, relationship_type, status) "
                "OUTPUT INSERTED.id VALUES (:b, :name, N'direct-client', N'active')"
            ),
            {"b": office_b, "name": f"Company B Client {sfx}"},
        ).scalar_one()
        requisition_a = connection.execute(
            text(
                "SELECT TOP 1 r.id FROM dbo.requisitions AS r INNER JOIN dbo.branches AS b ON b.id = r.branch_id "
                "WHERE b.tenant_id = :t ORDER BY r.id"
            ),
            {"t": tenant_a},
        ).scalar()
        client_a = connection.execute(
            text(
                "SELECT TOP 1 c.id FROM dbo.client_companies AS c INNER JOIN dbo.branches AS b ON b.id = c.branch_id "
                "WHERE b.tenant_id = :t ORDER BY c.id"
            ),
            {"t": tenant_a},
        ).scalar()

    headers_b = _login(client, email_b, B_PASSWORD)
    assert headers_b, "company B admin could not sign in"
    headers_exec_b = _login(client, email_exec_b, B_PASSWORD)
    assert headers_exec_b, "company B exec could not sign in"
    w = {
        "client": client, "engine": engine, "sfx": sfx,
        "a": headers_a, "b": headers_b, "exec_b": headers_exec_b,
        "tenant_a": tenant_a, "tenant_b": int(tenant_b),
        "office_a": int(office_a), "office_b": int(office_b),
        "admin_a_id": admin_a_id, "admin_b_id": int(admin_b_id),
        "client_a": client_a, "client_b": int(client_b), "requisition_a": requisition_a,
        "email_b": email_b,
    }
    yield w
    client.close()
    _cleanup(engine, w)


def _cleanup(engine, w) -> None:
    """Best effort; never masks a result."""
    statements = [
        ("DELETE FROM dbo.user_sessions WHERE user_id IN (SELECT id FROM dbo.users WHERE tenant_id = :t)", {}),
        ("DELETE FROM dbo.user_branch_roles WHERE user_id IN (SELECT id FROM dbo.users WHERE tenant_id = :t)", {}),
        ("DELETE FROM dbo.client_companies WHERE branch_id = :office", {}),
        ("DELETE FROM dbo.company_entities WHERE tenant_id = :t", {}),
        ("DELETE FROM dbo.users WHERE tenant_id = :t", {}),
        ("DELETE FROM dbo.role_permissions WHERE role_id IN (SELECT id FROM dbo.roles WHERE tenant_id = :t)", {}),
        ("DELETE FROM dbo.roles WHERE tenant_id = :t", {}),
        ("DELETE FROM dbo.locations WHERE tenant_id = :t", {}),
        ("DELETE FROM dbo.branches WHERE tenant_id = :t", {}),
        ("DELETE FROM dbo.tenants WHERE id = :t", {}),
    ]
    for sql, _ in statements:
        try:
            with engine.begin() as connection:
                connection.execute(text(sql), {"t": w["tenant_b"], "office": w["office_b"]})
        except Exception:  # noqa: BLE001
            pass


def _ids(response) -> set[int]:
    assert response.status_code == 200, response.text
    return {int(item["id"]) for item in response.json()["items"]}


# ---- lists ----------------------------------------------------------------

def test_each_company_lists_only_its_own_offices(world) -> None:
    c = world["client"]
    assert _ids(c.get(f"{API}/locations/?page_size=100", headers=world["b"])) == {world["office_b"]}
    assert world["office_b"] not in _ids(c.get(f"{API}/locations/?page_size=100", headers=world["a"]))


def test_company_b_cannot_list_company_a_records(world) -> None:
    c = world["client"]
    if world["requisition_a"]:
        assert world["requisition_a"] not in _ids(c.get(f"{API}/requisitions/?page_size=100", headers=world["exec_b"]))
    if world["client_a"]:
        assert world["client_a"] not in _ids(c.get(f"{API}/clients/?page_size=100", headers=world["exec_b"]))
    users_b = _ids(c.get(f"{API}/users/?page_size=100", headers=world["b"]))
    assert world["admin_a_id"] not in users_b


def test_company_a_cannot_list_company_b_records(world) -> None:
    c = world["client"]
    assert world["client_b"] not in _ids(c.get(f"{API}/clients/?page_size=100", headers=world["a"]))
    assert world["admin_b_id"] not in _ids(c.get(f"{API}/users/?page_size=100", headers=world["a"]))


# ---- direct ids answer 404 (never 403: foreign ids can't be probed) ----------

def test_direct_reads_across_companies_are_404(world) -> None:
    c = world["client"]
    if world["requisition_a"]:
        assert c.get(f"{API}/requisitions/{world['requisition_a']}", headers=world["exec_b"]).status_code == 404
    if world["client_a"]:
        assert c.get(f"{API}/clients/{world['client_a']}", headers=world["exec_b"]).status_code == 404
    assert c.get(f"{API}/clients/{world['client_b']}", headers=world["a"]).status_code == 404
    assert c.get(f"{API}/users/{world['admin_a_id']}", headers=world["b"]).status_code == 404
    assert c.get(f"{API}/users/{world['admin_b_id']}", headers=world["a"]).status_code == 404
    assert c.get(f"{API}/locations/{world['office_a']}", headers=world["b"]).status_code == 404
    assert c.get(f"{API}/locations/{world['office_b']}", headers=world["a"]).status_code == 404


def test_company_admin_cannot_name_another_companys_office_in_a_filter(world) -> None:
    c = world["client"]
    response = c.get(f"{API}/requisitions/?location_id={world['office_b']}", headers=world["a"])
    assert response.status_code in (403, 404)


# ---- writes cannot reference the other company -----------------------------

def test_cannot_create_user_on_another_companys_office(world) -> None:
    c = world["client"]
    role_id = world["engine"].connect().execute(
        text("SELECT id FROM dbo.roles WHERE code = N'admin' AND tenant_id IS NULL")
    ).scalar_one()
    response = c.post(
        f"{API}/users/",
        headers=world["b"],
        json={
            "full_name": "Cross Company",
            "email": f"cross-{world['sfx']}@example.com",
            "employee_code": f"X-{world['sfx']}",
            "primary_location_id": world["office_a"],
            "primary_role_id": int(role_id),
        },
    )
    assert response.status_code == 404, response.text


def test_cannot_create_requisition_for_another_companys_client(world) -> None:
    if not world["client_a"]:
        pytest.skip("company A has no client")
    c = world["client"]
    response = c.post(
        f"{API}/requisitions/",
        headers=world["exec_b"],
        json={
            "client_id": world["client_a"],
            "location_id": world["office_b"],
            "title": f"Cross {world['sfx']}",
            "primary_owner_user_id": world["admin_b_id"],
            "openings_count": 1,
            "target_closure_date": "2027-01-31",
            "job_description": "Cross-company reference must be refused.",
        },
    )
    assert response.status_code == 404, response.text
    assert response.json()["detail"] == "Client was not found"


# ---- roles ----------------------------------------------------------------

def test_company_roles_are_private_and_system_roles_read_only(world) -> None:
    c = world["client"]
    created = c.post(
        f"{API}/roles/",
        headers=world["b"],
        json={"name": f"B Recruiter {world['sfx']}", "code": f"b-recruiter-{world['sfx']}", "description": "B only"},
    )
    assert created.status_code == 201, created.text
    role_b = created.json()["id"]
    assert role_b not in _ids(c.get(f"{API}/roles/?page_size=100", headers=world["a"]))
    assert c.get(f"{API}/roles/{role_b}", headers=world["a"]).status_code == 404
    assert role_b in _ids(c.get(f"{API}/roles/?page_size=100", headers=world["b"]))

    admin_role = world["engine"].connect().execute(
        text("SELECT id FROM dbo.roles WHERE code = N'admin' AND tenant_id IS NULL")
    ).scalar_one()
    rename = c.patch(f"{API}/roles/{admin_role}", headers=world["b"], json={"name": "Hijacked"})
    assert rename.status_code == 403, rename.text


# ---- company status gates sign-in -----------------------------------------

def test_suspended_company_cannot_sign_in(world) -> None:
    engine = world["engine"]
    with engine.begin() as connection:
        connection.execute(text("UPDATE dbo.tenants SET status = N'suspended' WHERE id = :t"), {"t": world["tenant_b"]})
    try:
        response = world["client"].post(f"{API}/auth/login", json={"email": world["email_b"], "password": B_PASSWORD})
        assert response.status_code == 403, response.text
        # an existing session stops working too
        assert world["client"].get(f"{API}/auth/me", headers=world["b"]).status_code in (401, 403)
    finally:
        with engine.begin() as connection:
            connection.execute(text("UPDATE dbo.tenants SET status = N'active' WHERE id = :t"), {"t": world["tenant_b"]})


# ---- D-03: the company admin is the control plane, by grant ------------------

def test_company_admin_passes_control_plane_routes_by_grant(world) -> None:
    c = world["client"]
    for path in ("/users/", "/roles/", "/locations/", "/approvals/", "/notifications/", "/reports/time-to-fill"):
        assert c.get(f"{API}{path}", headers=world["b"]).status_code == 200, path
    me = c.get(f"{API}/permissions/me", headers=world["b"]).json()
    assert "scope.company" in me["permissions"]


def test_company_admin_is_denied_execution_routes(world) -> None:
    c = world["client"]
    for path in ("/candidates/", "/requisitions/", "/clients/", "/pipeline/board"):
        assert c.get(f"{API}{path}", headers=world["b"]).status_code == 403, path


# ---- company settings are per company (migration 012) -----------------------

def test_company_profile_is_per_company(world) -> None:
    c = world["client"]
    a = c.get(f"{API}/settings/profile", headers=world["a"])
    b = c.get(f"{API}/settings/profile", headers=world["b"])
    assert a.status_code == 200 and b.status_code == 200, (a.text, b.text)
    assert a.json()["id"] != b.json()["id"]
    assert b.json()["display_name"].startswith("Company B")
    renamed = c.patch(f"{API}/settings/profile", headers=world["b"], json={"hq_city": f"B-City-{world['sfx']}"})
    assert renamed.status_code == 200
    assert c.get(f"{API}/settings/profile", headers=world["a"]).json()["hq_city"] != f"B-City-{world['sfx']}"
