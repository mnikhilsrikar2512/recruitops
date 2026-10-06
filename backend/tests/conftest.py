from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.api import deps
from app.api.deps import get_engine, get_current_auth_context
from app.main import create_application


class _AllPermissions(frozenset):
    """Contains every code."""

    def __contains__(self, item: object) -> bool:
        return True


@pytest.fixture(autouse=True)
def _stub_admin_grants(monkeypatch):
    """Unit tests run against a MagicMock engine, so no grant can be resolved.
    Hand-built ``role_code="admin"`` stub contexts stand for a user whose roles
    grant everything (what the old role-code bypass gave them). Real grants —
    including the D-03 Admin template — are proven by the DB-backed tests and
    the live smoke against a seeded database, where this shim never applies."""
    from sqlalchemy.engine import Engine

    from app.api.v1 import agents as agents_api
    from app.services import agents as agents_service

    def wrap(original):
        def resolved(engine, auth_context):
            granted = original(engine, auth_context)
            if (
                not granted
                and not isinstance(engine, Engine)
                and getattr(getattr(auth_context, "user", None), "role_code", None) == "admin"
            ):
                return _AllPermissions()
            return granted
        return resolved

    monkeypatch.setattr(deps, "resolved_permissions_for", wrap(deps.resolved_permissions_for))
    monkeypatch.setattr(agents_api, "_resolved_permissions", wrap(agents_api._resolved_permissions))
    monkeypatch.setattr(agents_service, "_resolved_permissions", wrap(agents_service._resolved_permissions))
    yield


@pytest.fixture(autouse=True)
def _clear_permission_cache():
    deps._permission_cache.clear()
    yield
    deps._permission_cache.clear()


def _auth_ctx(user_id: int = 1, role_code: str = "admin", location_id: int = 1) -> SimpleNamespace:
    return SimpleNamespace(
        session_id=1,
        session_token_hash="abc123",
        user=SimpleNamespace(
            id=user_id,
            role_code=role_code,
            location_id=location_id,
            full_name="Test User",
            email="test@example.com",
            business_title="Recruiter",
            role_name="Recruiter",
            role_id=1,
            status="active",
        ),
    )


def _make_app(auth_context=None):
    app = create_application()
    engine_mock = MagicMock()
    app.dependency_overrides[get_engine] = lambda: engine_mock
    if auth_context is not None:
        app.dependency_overrides[get_current_auth_context] = lambda: auth_context
    get_engine.cache_clear()
    return app, TestClient(app, raise_server_exceptions=False)
