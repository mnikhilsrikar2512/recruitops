"""HTTP tests for self-service Profile APIs.

Tests the full HTTP request/response cycle through FastAPI's TestClient
for PATCH /auth/profile and POST /auth/password/change.
"""
from types import SimpleNamespace
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.main import create_application
from app.api.deps import get_engine, get_current_auth_context
from app.services.auth import AuthContext
from tests.stubs import make_login_user_record


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _auth_ctx(user_id: int = 22, location_id: int = 4, role_code: str = "admin") -> AuthContext:
    user = make_login_user_record(
        user_id=user_id,
        email="test@example.com",
        role_code=role_code,
        location_id=location_id,
        full_name="Test User",
        business_title="Recruiter",
        role_id=1,
        role_name="Recruiter",
        location_code="NYC",
        location_name="New York",
        status="active",
        force_password_change_on_first_login=False,
        phone="+1-555-0100",
    )
    return AuthContext(session_id=1, session_token_hash="tok_hash", user=user)


def _make_app(auth_ctx: AuthContext | None = None) -> tuple[FastAPI, TestClient]:
    get_engine.cache_clear()
    app = create_application()
    mock_engine = MagicMock()
    app.dependency_overrides[get_engine] = lambda: mock_engine
    if auth_ctx is not None:
        app.dependency_overrides[get_current_auth_context] = lambda: auth_ctx
    return app, TestClient(app, raise_server_exceptions=False)


def _stub_profile_write(monkeypatch, *, full_name="Test User", phone="+1-555-0100"):
    """Stub the dedicated profile repo write + audit + login refresh."""
    captured = {}

    def mock_update(engine, user_id, **kwargs):
        captured["user_id"] = user_id
        captured["kwargs"] = kwargs

    monkeypatch.setattr("app.services.auth.update_own_profile_fields", mock_update)
    monkeypatch.setattr("app.services.auth.insert_audit_log", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        "app.services.auth.find_user_for_login",
        lambda engine, email: make_login_user_record(full_name=full_name, phone=phone),
    )
    return captured


# ===========================================================================
# PATCH /auth/profile
# ===========================================================================

class TestUpdateProfileEndpoint:
    """PATCH /api/v1/auth/profile"""

    def test_profile_requires_auth(self):
        _, client = _make_app(auth_ctx=None)
        resp = client.patch("/api/v1/auth/profile", json={"full_name": "New Name"})
        assert resp.status_code in (401, 403)

    def test_empty_body_returns_422(self):
        _, client = _make_app(_auth_ctx())
        resp = client.patch("/api/v1/auth/profile", json={})
        assert resp.status_code == 422

    def test_name_only_update(self, monkeypatch):
        captured = _stub_profile_write(monkeypatch, full_name="Updated Name")
        _, client = _make_app(_auth_ctx())

        resp = client.patch("/api/v1/auth/profile", json={"full_name": "Updated Name"})
        assert resp.status_code == 200
        assert resp.json()["user"]["full_name"] == "Updated Name"
        assert captured["kwargs"]["has_full_name"] is True
        assert captured["kwargs"]["has_phone"] is False

    def test_phone_clear_sends_null(self, monkeypatch):
        """When user clears phone field, phone should be sent as null."""
        captured = _stub_profile_write(monkeypatch, phone=None)
        _, client = _make_app(_auth_ctx())

        resp = client.patch("/api/v1/auth/profile", json={"phone": ""})
        assert resp.status_code == 200
        assert captured["kwargs"]["has_phone"] is True
        assert captured["kwargs"]["phone"] is None

    def test_phone_not_included_when_not_sent(self, monkeypatch):
        """When phone key is absent from request, it should not be written."""
        captured = _stub_profile_write(monkeypatch, full_name="Name Only")
        _, client = _make_app(_auth_ctx())

        resp = client.patch("/api/v1/auth/profile", json={"full_name": "Name Only"})
        assert resp.status_code == 200
        assert captured["kwargs"]["has_phone"] is False

    def test_whitespace_name_returns_422(self, monkeypatch):
        """Whitespace-only full_name must be rejected, not a silent no-op."""
        _stub_profile_write(monkeypatch)
        _, client = _make_app(_auth_ctx())

        resp = client.patch("/api/v1/auth/profile", json={"full_name": "   "})
        assert resp.status_code == 422

    def test_whitespace_phone_normalized_to_none(self, monkeypatch):
        """Whitespace-only phone should become None (cleared)."""
        captured = _stub_profile_write(monkeypatch, phone=None)
        _, client = _make_app(_auth_ctx())

        resp = client.patch("/api/v1/auth/profile", json={"phone": "   "})
        assert resp.status_code == 200
        assert captured["kwargs"]["has_phone"] is True
        assert captured["kwargs"]["phone"] is None

    def test_both_fields_update(self, monkeypatch):
        captured = _stub_profile_write(
            monkeypatch, full_name="Both Updated", phone="+1-555-9999"
        )
        _, client = _make_app(_auth_ctx())

        resp = client.patch("/api/v1/auth/profile", json={
            "full_name": "Both Updated",
            "phone": "+1-555-9999",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["user"]["full_name"] == "Both Updated"
        assert data["user"]["phone"] == "+1-555-9999"
        assert captured["kwargs"]["has_full_name"] is True
        assert captured["kwargs"]["has_phone"] is True

    def test_does_not_call_admin_update_user_service(self, monkeypatch):
        """Self-profile must not go through admin update_user_service."""
        called = {"admin": False}

        def forbid_admin(*args, **kwargs):
            called["admin"] = True
            raise AssertionError("update_user_service must not be used for self-profile")

        monkeypatch.setattr("app.services.users.update_user_service", forbid_admin)
        _stub_profile_write(monkeypatch, full_name="Safe Name")
        _, client = _make_app(_auth_ctx())

        resp = client.patch("/api/v1/auth/profile", json={"full_name": "Safe Name"})
        assert resp.status_code == 200
        assert called["admin"] is False


# ===========================================================================
# POST /auth/password/change
# ===========================================================================

class TestPasswordChangeEndpoint:
    """POST /api/v1/auth/password/change"""

    def test_password_change_requires_auth(self):
        _, client = _make_app(auth_ctx=None)
        resp = client.post("/api/v1/auth/password/change", json={
            "current_password": "old",
            "new_password": "new",
        })
        assert resp.status_code in (401, 403)

    def test_password_change_empty_body_returns_422(self):
        _, client = _make_app(_auth_ctx())
        resp = client.post("/api/v1/auth/password/change", json={})
        assert resp.status_code == 422

    def test_password_change_missing_new_password_returns_422(self):
        _, client = _make_app(_auth_ctx())
        resp = client.post("/api/v1/auth/password/change", json={
            "current_password": "old",
        })
        assert resp.status_code == 422

    def test_password_change_short_new_password_returns_422(self):
        _, client = _make_app(_auth_ctx())
        resp = client.post("/api/v1/auth/password/change", json={
            "current_password": "old",
            "new_password": "short",
        })
        assert resp.status_code == 422

    def test_password_change_wrong_current_returns_400(self, monkeypatch):
        from app.core.security import sha256_hex
        correct_hash = f"sha256:{sha256_hex('correctpass')}"
        monkeypatch.setattr(
            "app.services.auth.find_user_for_login",
            lambda engine, email: SimpleNamespace(password_hash=correct_hash),
        )
        _, client = _make_app(_auth_ctx())

        resp = client.post("/api/v1/auth/password/change", json={
            "current_password": "wrongpass",
            "new_password": "NewSecurePass123!",
        })
        assert resp.status_code == 400
        assert "incorrect" in resp.json()["detail"].lower()

    def test_password_change_correct_returns_200(self, monkeypatch):
        from app.core.security import sha256_hex
        correct_hash = f"sha256:{sha256_hex('oldpass')}"
        monkeypatch.setattr(
            "app.services.auth.find_user_for_login",
            lambda engine, email: SimpleNamespace(password_hash=correct_hash),
        )
        monkeypatch.setattr(
            "app.services.auth.update_user_password_state",
            lambda engine, **kwargs: None,
        )
        _, client = _make_app(_auth_ctx())

        resp = client.post("/api/v1/auth/password/change", json={
            "current_password": "oldpass",
            "new_password": "NewSecurePass123!",
        })
        assert resp.status_code == 200
        assert "success" in resp.json()["message"].lower()


# ===========================================================================
# Profile route registration
# ===========================================================================

class TestProfileRoutesRegistered:
    def test_profile_route_registered(self):
        from app.main import app
        paths = app.openapi()["paths"]
        assert "/api/v1/auth/profile" in paths

    def test_password_change_route_registered(self):
        from app.main import app
        paths = app.openapi()["paths"]
        assert "/api/v1/auth/password/change" in paths
