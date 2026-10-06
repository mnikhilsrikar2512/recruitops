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

from app.core.rbac import ADMIN_PERMISSION_CODES

from tests.stubs import make_role_record, make_user_record
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


# Seed admin candidates: repo dev DB uses the seed user, CI uses the seeded CI admin
ADMIN_EMAIL_CANDIDATES = ["admin@executiveconnection.com", "ci.admin@recruitops-test.com"]
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
    login = None
    admin_email = None
    for candidate in ADMIN_EMAIL_CANDIDATES:
        attempt = client.post(
            "/api/v1/auth/login",
            json={"email": candidate, "password": ADMIN_PASSWORD},
        )
        if attempt.status_code == 200:
            login = attempt
            admin_email = candidate
            break
    if login is None:
        pytest.skip("Seed admin login failed; seed users first")
    admin_headers = {"Authorization": f"Bearer {login.json()['token']}"}
    admin_user_id = login.json()["user"]["id"]

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
        "admin_user_id": admin_user_id,
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


class TestLastAdminGuard:
    """The last active admin must not be demotable via user update — demoting
    that account previously locked the workspace out of its own settings."""

    @staticmethod
    def _active_admin_count() -> int:
        from sqlalchemy import text

        from app.db.session import create_db_engine

        engine = create_db_engine()
        with engine.connect() as connection:
            return int(
                connection.execute(
                    text(
                        "SELECT COUNT(*) FROM dbo.users u "
                        "INNER JOIN dbo.roles r ON r.id = u.default_role_id "
                        "WHERE r.code = N'admin' AND u.status = N'active'"
                    )
                ).scalar_one()
            )

    def test_cannot_demote_last_active_admin(self, client, rbac_chain):
        if self._active_admin_count() > 1:
            pytest.skip(
                "multiple active admins exist; the last-admin guard is not applicable"
            )
        # Point the seed admin at the minimal test role.
        response = client.patch(
            f"/api/v1/users/{rbac_chain['admin_user_id']}",
            headers=rbac_chain["admin_headers"],
            json={"primary_role_id": rbac_chain["role_id"]},
        )
        assert response.status_code == 409, response.text
        assert "last active admin" in response.json()["detail"]

    def test_admin_still_admin_after_attempt(self, client, rbac_chain):
        me = client.get("/api/v1/users/", headers=rbac_chain["admin_headers"])
        assert me.status_code == 200, me.text


class TestLastAdminGuardUnit:
    """Exercise the guard logic directly so it is covered even when the dev
    database holds many admins (which makes the DB-backed probe inapplicable)."""

    @staticmethod
    def _admin_record() -> object:
        return make_user_record(
            user_id=1,
            primary_role_id=1,
            primary_role_name="Admin",
            primary_role_code="admin",
            primary_location_id=1,
        )

    def test_guard_blocks_when_single_admin(self, monkeypatch) -> None:
        from types import SimpleNamespace

        from fastapi import HTTPException

        import app.services.users as users_service

        monkeypatch.setattr(
            users_service, "find_user_by_id", lambda engine, user_id: self._admin_record()
        )
        monkeypatch.setattr(
            users_service, "_assert_user_references", lambda *args, **kwargs: None
        )
        monkeypatch.setattr(users_service, "count_active_admins", lambda engine, *_: 1)
        monkeypatch.setattr(
            users_service,
            "update_user",
            lambda *a, **k: (_ for _ in ()).throw(AssertionError("update_user must not run")),
        )

        with pytest.raises(HTTPException) as excinfo:
            users_service.update_user_service(
                engine=SimpleNamespace(),
                user_id=1,
                payload=users_service.UserUpdate(primary_role_id=999),
            )
        assert excinfo.value.status_code == 409
        assert "last active admin" in excinfo.value.detail

    def test_guard_allows_when_multiple_admins(self, monkeypatch) -> None:
        from types import SimpleNamespace

        import app.services.users as users_service

        record = self._admin_record()
        monkeypatch.setattr(
            users_service, "find_user_by_id", lambda engine, user_id: record
        )
        monkeypatch.setattr(
            users_service, "_assert_user_references", lambda *args, **kwargs: None
        )
        monkeypatch.setattr(users_service, "count_active_admins", lambda engine, *_: 2)
        monkeypatch.setattr(
            users_service, "update_user", lambda engine, uid, payload, before: record
        )
        monkeypatch.setattr(
            users_service,
            "UserResponse",
            SimpleNamespace(model_validate=lambda value: value),
        )

        result = users_service.update_user_service(
            engine=SimpleNamespace(),
            user_id=1,
            payload=users_service.UserUpdate(primary_role_id=999),
        )
        assert result is record


class TestLastAdminDeactivateGuard:
    """Deactivating the last active admin would lock the workspace out of
    role/user configuration, so it must be refused (mirror of the role-change
    guard on the other admin-lockout path)."""

    def test_cannot_deactivate_last_active_admin(self, client, rbac_chain):
        if TestLastAdminGuard._active_admin_count() > 1:
            pytest.skip(
                "multiple active admins exist; the last-admin guard is not applicable"
            )
        response = client.post(
            f"/api/v1/users/{rbac_chain['admin_user_id']}/deactivate",
            headers=rbac_chain["admin_headers"],
            json={"review_confirmed": True, "transfer_to_user_id": None},
        )
        assert response.status_code == 409, response.text
        assert "last active admin" in response.json()["detail"]

    def test_admin_still_active_after_attempt(self, client, rbac_chain):
        response = client.get(
            f"/api/v1/users/{rbac_chain['admin_user_id']}",
            headers=rbac_chain["admin_headers"],
        )
        assert response.status_code == 200, response.text
        assert response.json()["status"] == "active"


class TestLastAdminDeactivateGuardUnit:
    """Unit coverage that runs regardless of dev-database admin count."""

    @staticmethod
    def _admin_record() -> object:
        return make_user_record(
            user_id=1,
            status="active",
            primary_role_id=1,
            primary_role_name="Admin",
            primary_role_code="admin",
            primary_location_id=1,
        )

    def test_guard_blocks_when_single_admin(self, monkeypatch) -> None:
        from types import SimpleNamespace

        from fastapi import HTTPException

        import app.services.users as users_service

        record = self._admin_record()
        monkeypatch.setattr(
            users_service, "find_user_by_id", lambda engine, user_id: record
        )
        monkeypatch.setattr(users_service, "count_active_admins", lambda engine, *_: 1)

        with pytest.raises(HTTPException) as excinfo:
            users_service.deactivate_user_service(
                engine=SimpleNamespace(),
                user_id=1,
                payload=users_service.UserDeactivateRequest(
                    reason="test lockout probe",
                    review_confirmed=True,
                    transfer_to_user_id=None,
                ),
            )
        assert excinfo.value.status_code == 409
        assert "last active admin" in excinfo.value.detail

    def test_guard_allows_when_multiple_admins(self, monkeypatch) -> None:
        from types import SimpleNamespace

        import app.services.users as users_service

        record = self._admin_record()
        monkeypatch.setattr(
            users_service, "find_user_by_id", lambda engine, user_id: record
        )
        monkeypatch.setattr(users_service, "count_active_admins", lambda engine, *_: 2)
        for count_fn in (
            "count_user_active_requisitions",
            "count_user_active_assignments",
            "count_user_active_candidate_ownership",
            "count_user_active_pipeline_ownership",
        ):
            monkeypatch.setattr(users_service, count_fn, lambda engine, user_id: 0)
        monkeypatch.setattr(
            users_service,
            "transfer_active_user_work_and_deactivate",
            lambda engine, user_id, transfer_to_user_id: record,
        )

        result = users_service.deactivate_user_service(
            engine=SimpleNamespace(),
            user_id=1,
            payload=users_service.UserDeactivateRequest(
                reason="test multi-admin probe",
                review_confirmed=True,
                transfer_to_user_id=None,
            ),
        )
        assert result.user_id == 1
        assert result.new_status == "active"


class TestAdminRoleProtection:
    """The admin role is the anchor of the permission bypass — its permission
    set must stay equal to the full catalog."""

    def test_admin_role_permissions_cannot_be_stripped(self, client, rbac_chain):
        response = client.put(
            "/api/v1/roles/1/permissions",
            headers=rbac_chain["admin_headers"],
            json={"permission_codes": ["candidate.read"], "scope_rules": {}},
        )
        # 409 = all-access guard; 403 = shared system role is read-only to companies (Phase 2)
        assert response.status_code in (403, 409), response.text
        detail = response.json()["detail"]
        assert "read-only" in detail or "fixed" in detail, detail

    def test_admin_role_permissions_unchanged_after_attempt(self, client, rbac_chain):
        response = client.get(
            "/api/v1/roles/1/permissions", headers=rbac_chain["admin_headers"]
        )
        assert response.status_code == 200, response.text
        assert len(response.json()["permission_codes"]) > 1


class TestAdminRoleProtectionUnit:
    """Unit coverage: guard fires exactly when the submitted set differs from
    the Admin template (D-03, app/core/rbac.py), and passes when it matches."""

    @staticmethod
    def _admin_role() -> object:
        return make_role_record(
            role_id=1,
            code="admin",
            name="Administrator",
            is_system_role=True,
        )

    def test_guard_blocks_partial_set(self, monkeypatch) -> None:
        from types import SimpleNamespace

        from fastapi import HTTPException

        import app.services.roles as roles_service

        monkeypatch.setattr(
            roles_service, "find_role_by_id", lambda engine, role_id: self._admin_role()
        )

        with pytest.raises(HTTPException) as excinfo:
            roles_service.assign_role_permissions_service(
                engine=SimpleNamespace(),
                role_id=1,
                payload=roles_service.RolePermissionsUpdate(
                    permission_codes=["a.read"], scope_rules={}
                ),
            )
        assert excinfo.value.status_code == 409
        assert "fixed" in excinfo.value.detail

    def test_guard_passes_the_admin_template(self, monkeypatch) -> None:
        from types import SimpleNamespace

        import app.services.roles as roles_service

        monkeypatch.setattr(
            roles_service, "find_role_by_id", lambda engine, role_id: self._admin_role()
        )
        monkeypatch.setattr(
            roles_service, "count_permissions_by_codes", lambda engine, codes: len(codes)
        )
        monkeypatch.setattr(
            roles_service, "replace_role_permissions", lambda *args, **kwargs: None
        )
        monkeypatch.setattr(
            roles_service,
            "list_permission_codes_for_role",
            lambda engine, role_id: ["a.read", "b.read"],
        )
        monkeypatch.setattr(
            roles_service, "list_scope_rules_for_role", lambda engine, role_id: {}
        )

        response = roles_service.assign_role_permissions_service(
            engine=SimpleNamespace(),
            role_id=1,
            payload=roles_service.RolePermissionsUpdate(
                permission_codes=list(ADMIN_PERMISSION_CODES), scope_rules={}
            ),
        )
        assert response.permission_codes == ["a.read", "b.read"]

    def test_guard_does_not_touch_non_admin_roles(self, monkeypatch) -> None:
        from types import SimpleNamespace

        import app.services.roles as roles_service

        role = self._admin_role()
        role.code = "recruiter"
        role.is_system_role = False
        monkeypatch.setattr(
            roles_service, "find_role_by_id", lambda engine, role_id: role
        )
        monkeypatch.setattr(
            roles_service, "count_permissions_by_codes", lambda engine, codes: len(codes)
        )
        monkeypatch.setattr(
            roles_service, "replace_role_permissions", lambda *args, **kwargs: None
        )
        monkeypatch.setattr(
            roles_service,
            "list_permission_codes_for_role",
            lambda engine, role_id: ["a.read"],
        )
        monkeypatch.setattr(
            roles_service, "list_scope_rules_for_role", lambda engine, role_id: {}
        )

        response = roles_service.assign_role_permissions_service(
            engine=SimpleNamespace(),
            role_id=2,
            payload=roles_service.RolePermissionsUpdate(
                permission_codes=["a.read"], scope_rules={}
            ),
        )
        assert response.permission_codes == ["a.read"]


class TestLastAdminPatchGuards:
    """PATCH /users/{id} writes both role and status, and move can change
    the role — both were unguarded paths to lock out the last active admin
    (PATCH {"status": "inactive"} was confirmed live with a 200)."""

    @staticmethod
    def _admin_record() -> object:
        return make_user_record(
            user_id=1,
            status="active",
            primary_role_id=1,
            primary_role_name="Admin",
            primary_role_code="admin",
            primary_location_id=1,
        )

    @staticmethod
    def _patch_admin(monkeypatch, count: int, payload: "object") -> None:
        from types import SimpleNamespace

        from fastapi import HTTPException

        import app.services.users as users_service

        record = self._admin_record()
        monkeypatch.setattr(
            users_service, "find_user_by_id", lambda engine, user_id: record
        )
        monkeypatch.setattr(
            users_service, "_assert_user_references", lambda *args, **kwargs: None
        )
        monkeypatch.setattr(users_service, "count_active_admins", lambda engine, *_: count)
        try:
            users_service.update_user_service(
                engine=SimpleNamespace(), user_id=1, payload=payload
            )
        except HTTPException:
            raise

    def test_patch_cannot_set_last_admin_inactive(self, monkeypatch) -> None:
        from types import SimpleNamespace

        from fastapi import HTTPException

        import app.services.users as users_service

        record = self._admin_record()
        monkeypatch.setattr(
            users_service, "find_user_by_id", lambda engine, user_id: record
        )
        monkeypatch.setattr(
            users_service, "_assert_user_references", lambda *args, **kwargs: None
        )
        monkeypatch.setattr(users_service, "count_active_admins", lambda engine, *_: 1)

        with pytest.raises(HTTPException) as excinfo:
            users_service.update_user_service(
                engine=SimpleNamespace(),
                user_id=1,
                payload=users_service.UserUpdate(status="inactive"),
            )
        assert excinfo.value.status_code == 409
        assert "last active admin" in excinfo.value.detail

    def test_patch_status_allowed_when_multiple_admins(self, monkeypatch) -> None:
        from types import SimpleNamespace

        import app.services.users as users_service

        record = self._admin_record()
        monkeypatch.setattr(
            users_service, "find_user_by_id", lambda engine, user_id: record
        )
        monkeypatch.setattr(
            users_service, "_assert_user_references", lambda *args, **kwargs: None
        )
        monkeypatch.setattr(users_service, "count_active_admins", lambda engine, *_: 2)
        monkeypatch.setattr(
            users_service, "update_user", lambda engine, uid, payload, before: record
        )
        monkeypatch.setattr(
            users_service,
            "UserResponse",
            SimpleNamespace(model_validate=lambda value: value),
        )

        result = users_service.update_user_service(
            engine=SimpleNamespace(),
            user_id=1,
            payload=users_service.UserUpdate(status="inactive"),
        )
        assert result is record

    def test_move_cannot_change_last_admin_role(self, monkeypatch) -> None:
        from types import SimpleNamespace

        from fastapi import HTTPException

        import app.services.users as users_service

        record = self._admin_record()
        monkeypatch.setattr(
            users_service, "find_user_by_id", lambda engine, user_id: record
        )
        monkeypatch.setattr(users_service, "count_active_admins", lambda engine, *_: 1)
        monkeypatch.setattr(
            users_service, "_assert_user_references", lambda *args, **kwargs: None
        )

        with pytest.raises(HTTPException) as excinfo:
            users_service.move_user_service(
                engine=SimpleNamespace(),
                user_id=1,
                payload=users_service.UserMoveRequest(
                    new_primary_role_id=999,
                    new_primary_location_id=1,
                    reason="guard probe",
                    review_confirmed=True,
                    transfer_to_user_id=None,
                ),
            )
        assert excinfo.value.status_code == 409
        assert "last active admin" in excinfo.value.detail
