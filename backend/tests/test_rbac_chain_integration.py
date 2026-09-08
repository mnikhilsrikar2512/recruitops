"""RBAC chain integration test.

Covers the full chain a workspace admin performs onboarding a teammate:

    admin login -> create role -> assign permissions -> create user
    -> issue setup link -> user sets password -> user logs in -> RBAC probes

The probes assert that a user with only ``candidate.read`` + ``notification.read``
can reach granted resources and is rejected everywhere else — most importantly
that ``role.read`` is NOT satisfied by ``user.read``/``settings.read`` (the alias
bypass that let any user with user-read access list and manage roles).

The DB-backed tests run against the real configured database and skip when it
is unreachable so the rest of the suite still passes in CI without SQL Server.
"""
import time
import uuid

import pytest
from fastapi.testclient import TestClient

from app.api.deps import _has_permission
from app.main import create_application


# ---------------------------------------------------------------------------
# Alias-map regression guard (no DB needed)
# ---------------------------------------------------------------------------


class TestPermissionAliases:
    """Lock the alias map: role management codes must not be satisfiable by
    unrelated read permissions."""

    def test_role_read_not_satisfied_by_user_read(self) -> None:
        assert _has_permission({"user.read"}, "role.read") is False

    def test_role_read_not_satisfied_by_settings_read(self) -> None:
        assert _has_permission({"settings.read"}, "role.read") is False

    def test_role_create_not_satisfied_by_settings_update(self) -> None:
        assert _has_permission({"settings.update"}, "role.create") is False

    def test_role_update_not_satisfied_by_settings_update(self) -> None:
        assert _has_permission({"settings.update"}, "role.update") is False

    def test_role_permissions_assign_not_satisfied_by_settings_update(self) -> None:
        assert _has_permission({"settings.update"}, "role.permissions.assign") is False

    def test_exact_grants_still_pass(self) -> None:
        assert _has_permission({"role.read"}, "role.read") is True
        assert _has_permission({"candidate.read"}, "candidate.read") is True
        assert _has_permission({"notification.read"}, "notification.read") is True


# ---------------------------------------------------------------------------
# Full chain against the real database
# ---------------------------------------------------------------------------


ADMIN_EMAIL = "admin@executiveconnection.com"
ADMIN_PASSWORD = "admin123"
# user.read is deliberately granted: the historical bypass aliased role.read to
# accept user.read, so any user who could list users could also list roles.
GRANTED_CODES = ["candidate.read", "notification.read", "user.read"]


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


@pytest.fixture(scope="module")
def client():
    if not _db_reachable():
        pytest.skip("Configured SQL Server database is not reachable")
    get_engine = None  # real engine is used; nothing to override
    app = create_application()
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


@pytest.fixture(scope="module")
def rbac_chain(client):
    """Run the full admin chain once for the whole module and share the result."""
    login = client.post(
        "/api/v1/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    if login.status_code != 200:
        pytest.skip(f"Seed admin login failed ({login.status_code}); seed users first")
    admin_headers = {"Authorization": f"Bearer {login.json()['token']}"}

    suffix = uuid.uuid4().hex[:8]
    role = client.post(
        "/api/v1/roles/",
        headers=admin_headers,
        json={
            "name": f"RBAC IT {suffix}",
            "code": f"rbac-it-{suffix}",
            "description": "Integration test role with minimal grants",
        },
    )
    assert role.status_code == 201, role.text
    role_id = role.json()["id"]

    assigned = client.put(
        f"/api/v1/roles/{role_id}/permissions",
        headers=admin_headers,
        json={"permission_codes": GRANTED_CODES, "scope_rules": {}},
    )
    assert assigned.status_code == 200, assigned.text
    assert sorted(assigned.json()["permission_codes"]) == sorted(GRANTED_CODES)

    user = client.post(
        "/api/v1/users/",
        headers=admin_headers,
        json={
            "full_name": "RBAC Integration User",
            "email": f"rbac-it-{suffix}@example.com",
            "employee_code": f"RBACIT-{suffix}",
            "primary_location_id": 1,
            "primary_role_id": role_id,
        },
    )
    assert user.status_code == 201, user.text
    user_id = user.json()["id"]

    reset = client.post(
        f"/api/v1/users/{user_id}/credentials/reset",
        headers=admin_headers,
        json={"mode": "setup-link", "issued_by_user_id": 1},
    )
    assert reset.status_code == 200, reset.text
    setup_token = reset.json()["setup_token"]
    assert setup_token, reset.text

    setup = client.post(
        "/api/v1/auth/password/setup",
        json={"token": setup_token, "new_password": "RbacChain123!"},
    )
    assert setup.status_code == 200, setup.text

    user_login = client.post(
        "/api/v1/auth/login",
        json={"email": f"rbac-it-{suffix}@example.com", "password": "RbacChain123!"},
    )
    assert user_login.status_code == 200, user_login.text
    user_headers = {"Authorization": f"Bearer {user_login.json()['token']}"}

    yield {
        "admin_headers": admin_headers,
        "user_headers": user_headers,
        "role_id": role_id,
        "user_id": user_id,
    }

    # Cleanup: deactivate the user and retire the role. Best effort — the run
    # must not fail because teardown hit an error.
    client.post(
        f"/api/v1/users/{user_id}/deactivate",
        headers=admin_headers,
        json={"reason": "integration test cleanup", "review_confirmed": True},
    )
    client.patch(
        f"/api/v1/roles/{role_id}",
        headers=admin_headers,
        json={"status": "inactive"},
    )


class TestRbacChain:
    def test_user_reaches_granted_resources(self, client, rbac_chain):
        candidates = client.get(
            "/api/v1/candidates/?page_size=1", headers=rbac_chain["user_headers"]
        )
        assert candidates.status_code == 200, candidates.text

        notifications = client.get(
            "/api/v1/notifications/?page_size=1", headers=rbac_chain["user_headers"]
        )
        assert notifications.status_code == 200, notifications.text

    def test_user_cannot_list_roles(self, client, rbac_chain):
        response = client.get("/api/v1/roles/", headers=rbac_chain["user_headers"])
        assert response.status_code == 403

    def test_user_cannot_create_roles(self, client, rbac_chain):
        response = client.post(
            "/api/v1/roles/",
            headers=rbac_chain["user_headers"],
            json={"name": "Escalation", "code": "escalation-attempt"},
        )
        assert response.status_code == 403

    def test_user_cannot_assign_role_permissions(self, client, rbac_chain):
        response = client.put(
            f"/api/v1/roles/{rbac_chain['role_id']}/permissions",
            headers=rbac_chain["user_headers"],
            json={"permission_codes": ["role.read"], "scope_rules": {}},
        )
        assert response.status_code == 403

    def test_user_read_grants_users_but_not_roles(self, client, rbac_chain):
        """user.read legitimately allows listing users — and must NOT leak into
        role management (the historical bypass)."""
        response = client.get("/api/v1/users/", headers=rbac_chain["user_headers"])
        assert response.status_code == 200

    def test_user_cannot_access_pipeline(self, client, rbac_chain):
        response = client.get("/api/v1/pipeline/board", headers=rbac_chain["user_headers"])
        assert response.status_code == 403

    def test_user_cannot_access_approvals(self, client, rbac_chain):
        response = client.get("/api/v1/approvals/", headers=rbac_chain["user_headers"])
        assert response.status_code == 403

    def test_resolved_permissions_match_grant(self, client, rbac_chain):
        me = client.get("/api/v1/permissions/me", headers=rbac_chain["user_headers"])
        if me.status_code == 404:
            pytest.skip("/permissions/me endpoint not mounted")
        assert me.status_code == 200, me.text
        payload = me.json()
        codes = set(payload.get("permissions") or payload.get("permission_codes") or payload)
        assert {"candidate.read", "notification.read", "user.read"} <= codes
        assert "role.read" not in codes
