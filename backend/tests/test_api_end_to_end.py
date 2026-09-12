"""End-to-end API tests for all new endpoints.

Tests the full HTTP request/response cycle through FastAPI's TestClient
with mocked database layer.
"""
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.main import create_application
from app.api.deps import get_engine, get_current_auth_context
from tests.stubs import make_login_user_record

from app.services.auth import AuthContext


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _auth_ctx(user_id: int = 22, location_id: int = 4, role_code: str = "admin") -> AuthContext:
    user = SimpleNamespace(
        id=user_id,
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
    )
    return AuthContext(session_id=1, session_token_hash="tok_hash", user=user)


def _make_app(auth_ctx: AuthContext | None = None) -> tuple[FastAPI, TestClient]:
    """Create a fresh app with mocked engine and optional auth context."""
    get_engine.cache_clear()
    app = create_application()

    mock_engine = MagicMock()
    app.dependency_overrides[get_engine] = lambda: mock_engine

    if auth_ctx is not None:
        app.dependency_overrides[get_current_auth_context] = lambda: auth_ctx

    return app, TestClient(app, raise_server_exceptions=False)


# ===========================================================================
# 1. PASSWORD FLOW ENDPOINTS
# ===========================================================================

class TestPasswordSetupEndpoint:
    """POST /api/v1/auth/password/setup"""

    def test_setup_password_invalid_token_returns_400(self, monkeypatch):
        monkeypatch.setattr(
            "app.services.auth.find_valid_password_reset_token",
            lambda engine, token_hash, purpose: None,
        )
        _, client = _make_app()

        resp = client.post("/api/v1/auth/password/setup", json={
            "token": "bad-token",
            "new_password": "SecurePass123!",
        })
        assert resp.status_code == 400

    def test_setup_password_valid_token_returns_200(self, monkeypatch):
        monkeypatch.setattr(
            "app.services.auth.find_valid_password_reset_token",
            lambda engine, token_hash, purpose: {"id": 1, "user_id": 22},
        )
        monkeypatch.setattr(
            "app.services.auth.update_user_password_state",
            lambda engine, **kwargs: None,
        )
        monkeypatch.setattr(
            "app.services.auth.mark_password_reset_token_used",
            lambda engine, token_id: None,
        )
        _, client = _make_app()

        resp = client.post("/api/v1/auth/password/setup", json={
            "token": "valid-token",
            "new_password": "SecurePass123!",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "message" in data
        assert "success" in data["message"].lower()


class TestForgotPasswordEndpoint:
    """POST /api/v1/auth/password/forgot"""

    def test_forgot_password_nonexistent_user_returns_200(self, monkeypatch):
        monkeypatch.setattr(
            "app.services.auth.find_user_by_email",
            lambda engine, email: None,
        )
        _, client = _make_app()

        resp = client.post("/api/v1/auth/password/forgot", json={
            "email": "unknown@example.com",
        })
        assert resp.status_code == 200
        assert "reset" in resp.json()["message"].lower()

    def test_forgot_password_existing_user_returns_200(self, monkeypatch):
        monkeypatch.setattr(
            "app.services.auth.find_user_by_email",
            lambda engine, email: make_login_user_record(),
        )
        monkeypatch.setattr(
            "app.services.auth.create_password_reset_token",
            lambda engine, **kwargs: None,
        )
        _, client = _make_app()

        resp = client.post("/api/v1/auth/password/forgot", json={
            "email": "test@example.com",
        })
        assert resp.status_code == 200


class TestResetPasswordEndpoint:
    """POST /api/v1/auth/password/reset"""

    def test_reset_password_invalid_token_returns_400(self, monkeypatch):
        monkeypatch.setattr(
            "app.services.auth.find_valid_password_reset_token",
            lambda engine, token_hash, purpose: None,
        )
        _, client = _make_app()

        resp = client.post("/api/v1/auth/password/reset", json={
            "token": "bad-token",
            "new_password": "SecurePass123!",
        })
        assert resp.status_code == 400

    def test_reset_password_valid_token_returns_200(self, monkeypatch):
        monkeypatch.setattr(
            "app.services.auth.find_valid_password_reset_token",
            lambda engine, token_hash, purpose: {"id": 1, "user_id": 22},
        )
        monkeypatch.setattr(
            "app.services.auth.update_user_password_state",
            lambda engine, **kwargs: None,
        )
        monkeypatch.setattr(
            "app.services.auth.mark_password_reset_token_used",
            lambda engine, token_id: None,
        )
        _, client = _make_app()

        resp = client.post("/api/v1/auth/password/reset", json={
            "token": "valid-token",
            "new_password": "SecurePass123!",
        })
        assert resp.status_code == 200
        assert "success" in resp.json()["message"].lower()


class TestChangePasswordEndpoint:
    """POST /api/v1/auth/password/change"""

    def test_change_password_requires_auth(self):
        _, client = _make_app(auth_ctx=None)

        resp = client.post("/api/v1/auth/password/change", json={
            "current_password": "old",
            "new_password": "new",
        })
        assert resp.status_code in (401, 403)

    def test_change_password_wrong_current_returns_400(self, monkeypatch):
        monkeypatch.setattr(
            "app.services.auth.find_user_for_login",
            lambda engine, email: SimpleNamespace(password_hash="sha256:abc"),
        )
        _, client = _make_app(_auth_ctx())

        resp = client.post("/api/v1/auth/password/change", json={
            "current_password": "wrong",
            "new_password": "SecurePass123!",
        })
        assert resp.status_code == 400

    def test_change_password_correct_returns_200(self, monkeypatch):
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
            "new_password": "SecurePass123!",
        })
        assert resp.status_code == 200
        assert "success" in resp.json()["message"].lower()


# ===========================================================================
# 2. NOTIFICATION ENDPOINTS
# ===========================================================================

class TestListNotificationsEndpoint:
    """GET /api/v1/notifications/"""

    def test_list_notifications_requires_auth(self):
        _, client = _make_app(auth_ctx=None)

        resp = client.get("/api/v1/notifications/")
        assert resp.status_code in (401, 403)

    def test_list_notifications_returns_200(self):
        with patch("app.api.deps.list_resolved_permissions", return_value=[]):
            with patch(
                "app.api.v1.notifications.list_notifications_service",
                return_value={"items": [], "meta": {"page": 1, "page_size": 20, "total": 0}},
            ):
                _, client = _make_app(_auth_ctx())
                resp = client.get("/api/v1/notifications/")
                assert resp.status_code == 200
                data = resp.json()
                assert "items" in data
                assert "meta" in data
                assert "total" in data["meta"]

    def test_list_notifications_with_filters(self):
        with patch("app.api.deps.list_resolved_permissions", return_value=[]):
            captured_filters = {}

            def mock_service(engine, ctx, filters):
                captured_filters["status"] = filters.status
                captured_filters["priority"] = filters.priority
                captured_filters["page"] = filters.page
                captured_filters["page_size"] = filters.page_size
                return {"items": [], "meta": {"page": 1, "page_size": 20, "total": 0}}

            with patch("app.api.v1.notifications.list_notifications_service", side_effect=mock_service):
                _, client = _make_app(_auth_ctx())
                resp = client.get("/api/v1/notifications/?status=unread&priority=high&page=2&page_size=10")
                assert resp.status_code == 200
                assert captured_filters["status"] == "unread"
                assert captured_filters["priority"] == "high"
                assert captured_filters["page"] == 2
                assert captured_filters["page_size"] == 10


class TestMarkNotificationReadEndpoint:
    """PATCH /api/v1/notifications/{id}/read"""

    def test_mark_read_requires_auth(self):
        _, client = _make_app(auth_ctx=None)

        resp = client.patch("/api/v1/notifications/1/read", json={})
        assert resp.status_code in (401, 403)

    def test_mark_read_missing_notification_returns_404(self):
        def raise_not_found(engine, ctx, nid):
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Notification not found")

        with patch("app.api.deps.list_resolved_permissions", return_value=[]):
            with patch("app.api.v1.notifications.mark_notification_read_service", side_effect=raise_not_found):
                _, client = _make_app(_auth_ctx())
                resp = client.patch("/api/v1/notifications/999/read", json={})
                assert resp.status_code == 404

    def test_mark_read_wrong_owner_returns_403(self):
        def raise_forbidden(engine, ctx, nid):
            from fastapi import HTTPException
            raise HTTPException(status_code=403, detail="Not your notification")

        with patch("app.api.deps.list_resolved_permissions", return_value=[]):
            with patch("app.api.v1.notifications.mark_notification_read_service", side_effect=raise_forbidden):
                _, client = _make_app(_auth_ctx())
                resp = client.patch("/api/v1/notifications/1/read", json={})
                assert resp.status_code == 403

    def test_mark_read_success_returns_200(self):
        with patch("app.api.deps.list_resolved_permissions", return_value=[]):
            with patch(
                "app.api.v1.notifications.mark_notification_read_service",
                return_value={"id": 1, "location_id": 4, "user_id": 22, "title": "Test", "message": "Body", "module_name": "candidate", "entity_type": "candidate", "entity_id": 1, "status": "read", "priority": "normal", "action_url": None, "read_at": "2024-01-01T00:00:00", "created_at": "2024-01-01T00:00:00", "updated_at": "2024-01-01T00:00:00"},
            ):
                _, client = _make_app(_auth_ctx())
                resp = client.patch("/api/v1/notifications/1/read", json={})
                assert resp.status_code == 200
                assert resp.json()["status"] == "read"


# ===========================================================================
# 3. FILE UPLOAD ENDPOINTS
# ===========================================================================

class TestFileUploadEndpoint:
    """POST /api/v1/candidates/{id}/upload"""

    def test_upload_requires_auth(self):
        _, client = _make_app(auth_ctx=None)

        resp = client.post("/api/v1/candidates/1/upload",
                          files={"file": ("test.pdf", b"content", "application/pdf")})
        assert resp.status_code in (401, 403)

    def test_upload_rejects_disallowed_extension(self):
        def reject_extension(engine, ctx, cid, file, doc_type):
            from fastapi import HTTPException
            raise HTTPException(status_code=422, detail="File extension not allowed")

        with patch("app.api.deps.list_resolved_permissions", return_value=[]):
            with patch("app.api.v1.candidates.upload_candidate_document_service", side_effect=reject_extension):
                _, client = _make_app(_auth_ctx())
                resp = client.post("/api/v1/candidates/1/upload",
                                  files={"file": ("malware.exe", b"MZ", "application/octet-stream")})
                assert resp.status_code in (400, 422)

    def test_upload_accepts_pdf(self):
        with patch("app.api.deps.list_resolved_permissions", return_value=[]):
            with patch(
                "app.api.v1.candidates.upload_candidate_document_service",
                new_callable=AsyncMock,
                return_value={"id": 1, "candidate_id": 1, "document_type": "other", "file_name": "resume.pdf", "file_path": "uploads/resume.pdf", "content_type": "application/pdf", "verification_status": "pending", "uploaded_by_user_id": 22, "verified_by_user_id": None, "verified_at": None, "created_at": "2024-01-01T00:00:00", "updated_at": "2024-01-01T00:00:00"},
            ):
                _, client = _make_app(_auth_ctx())
                resp = client.post("/api/v1/candidates/1/upload",
                                  files={"file": ("resume.pdf", b"%PDF-1.4 content", "application/pdf")})
                assert resp.status_code == 201
                assert resp.json()["file_name"] == "resume.pdf"

    def test_upload_rejects_invalid_candidate(self):
        def raise_not_found(engine, ctx, cid, file, content_type):
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Candidate not found")

        with patch("app.api.deps.list_resolved_permissions", return_value=[]):
            with patch("app.api.v1.candidates.upload_candidate_document_service", side_effect=raise_not_found):
                _, client = _make_app(_auth_ctx())
                resp = client.post("/api/v1/candidates/999/upload",
                                  files={"file": ("resume.pdf", b"content", "application/pdf")})
                assert resp.status_code == 404


class TestFileServeEndpoint:
    """GET /api/v1/files/{path}"""

    def test_serve_file_requires_auth(self):
        _, client = _make_app(auth_ctx=None)

        resp = client.get("/api/v1/files/uploads/test.pdf")
        assert resp.status_code in (401, 403)

    def test_serve_file_not_found_returns_404(self):
        _, client = _make_app(_auth_ctx())

        resp = client.get("/api/v1/files/nonexistent.pdf")
        assert resp.status_code == 404


# ===========================================================================
# 4. AUTH ENDPOINTS
# ===========================================================================

class TestLoginEndpoint:
    """POST /api/v1/auth/login"""

    def test_login_invalid_credentials_returns_401(self, monkeypatch):
        monkeypatch.setattr(
            "app.services.auth.find_user_for_login",
            lambda engine, email: None,
        )
        _, client = _make_app()

        resp = client.post("/api/v1/auth/login", json={
            "email": "bad@example.com",
            "password": "wrong",
        })
        assert resp.status_code == 401

    def test_login_valid_credentials_returns_200(self, monkeypatch):
        from app.core.security import sha256_hex
        correct_hash = f"sha256:{sha256_hex('correctpass')}"
        monkeypatch.setattr(
            "app.services.auth.find_user_for_login",
            lambda engine, email: make_login_user_record(
                password_hash=correct_hash, role_id=1, location_id=4,
                location_code="NYC", location_name="New York",
            ),
        )
        monkeypatch.setattr(
            "app.services.auth.insert_user_session",
            lambda engine, **kwargs: SimpleNamespace(id=1, expires_at="2024-12-31T23:59:59"),
        )
        monkeypatch.setattr(
            "app.services.auth.update_last_login",
            lambda engine, user_id: None,
        )
        _, client = _make_app()

        resp = client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "correctpass",
        })
        assert resp.status_code == 200
        assert "token" in resp.json()


class TestLogoutEndpoint:
    """POST /api/v1/auth/logout"""

    def test_logout_requires_auth(self):
        _, client = _make_app(auth_ctx=None)

        resp = client.post("/api/v1/auth/logout")
        assert resp.status_code in (401, 403)

    def test_logout_returns_200(self, monkeypatch):
        monkeypatch.setattr(
            "app.services.auth.revoke_session_by_hash",
            lambda engine, token_hash: None,
        )
        _, client = _make_app(_auth_ctx())

        resp = client.post("/api/v1/auth/logout")
        assert resp.status_code == 200
        assert "logged out" in resp.json()["message"].lower()


class TestMeEndpoint:
    """GET /api/v1/auth/me"""

    def test_me_requires_auth(self):
        _, client = _make_app(auth_ctx=None)

        resp = client.get("/api/v1/auth/me")
        assert resp.status_code in (401, 403)

    def test_me_returns_session_info(self):
        _, client = _make_app(_auth_ctx())

        resp = client.get("/api/v1/auth/me")
        assert resp.status_code == 200
        data = resp.json()
        assert data["user"]["id"] == 22
        assert data["primary_role"]["code"] == "admin"


# ===========================================================================
# 5. HEALTH ENDPOINT
# ===========================================================================

class TestHealthEndpoint:
    """GET /api/v1/health"""

    def test_health_returns_200(self):
        _, client = _make_app()

        resp = client.get("/api/v1/health")
        assert resp.status_code == 200


# ===========================================================================
# 6. ROUTE REGISTRATION
# ===========================================================================

class TestRouteRegistration:
    """Verify all new routes are registered in the app."""

    def test_all_password_routes_registered(self):
        from app.main import app
        paths = app.openapi()["paths"]

        assert "/api/v1/auth/password/setup" in paths
        assert "/api/v1/auth/password/forgot" in paths
        assert "/api/v1/auth/password/reset" in paths
        assert "/api/v1/auth/password/change" in paths

    def test_notification_routes_registered(self):
        from app.main import app
        paths = app.openapi()["paths"]

        assert "/api/v1/notifications/" in paths
        assert "/api/v1/notifications/{notification_id}/read" in paths

    def test_file_upload_route_registered(self):
        from app.main import app
        paths = app.openapi()["paths"]

        assert "/api/v1/candidates/{candidate_id}/upload" in paths

    def test_file_serve_route_registered(self):
        from app.main import app
        paths = app.openapi()["paths"]

        assert "/api/v1/files/{file_path}" in paths

    def test_auth_routes_registered(self):
        from app.main import app
        paths = app.openapi()["paths"]

        assert "/api/v1/auth/login" in paths
        assert "/api/v1/auth/logout" in paths
        assert "/api/v1/auth/me" in paths


# ===========================================================================
# 7. VALIDATION ERROR HANDLING
# ===========================================================================

class TestValidationErrors:
    """Verify validation errors return proper 422 responses."""

    def test_login_missing_fields_returns_422(self):
        _, client = _make_app()

        resp = client.post("/api/v1/auth/login", json={})
        assert resp.status_code == 422

    def test_password_setup_missing_fields_returns_422(self):
        _, client = _make_app()

        resp = client.post("/api/v1/auth/password/setup", json={})
        assert resp.status_code == 422

    def test_forgot_password_missing_email_returns_422(self):
        _, client = _make_app()

        resp = client.post("/api/v1/auth/password/forgot", json={})
        assert resp.status_code == 422

    def test_notification_list_invalid_page_returns_422(self):
        with patch("app.api.deps.list_resolved_permissions", return_value=[]):
            _, client = _make_app(_auth_ctx())
            resp = client.get("/api/v1/notifications/?page=0")
            assert resp.status_code == 422

    def test_notification_list_invalid_page_size_returns_422(self):
        with patch("app.api.deps.list_resolved_permissions", return_value=[]):
            _, client = _make_app(_auth_ctx())
            resp = client.get("/api/v1/notifications/?page_size=200")
            assert resp.status_code == 422


# ===========================================================================
# 8. ERROR RESPONSE FORMAT
# ===========================================================================

class TestErrorFormat:
    """Verify error responses have consistent format."""

    def test_401_has_detail_field(self):
        _, client = _make_app(auth_ctx=None)

        resp = client.get("/api/v1/auth/me")
        assert resp.status_code in (401, 403)
        data = resp.json()
        assert "detail" in data

    def test_422_has_detail_and_errors(self):
        _, client = _make_app()

        resp = client.post("/api/v1/auth/login", json={})
        assert resp.status_code == 422
        data = resp.json()
        assert "detail" in data
