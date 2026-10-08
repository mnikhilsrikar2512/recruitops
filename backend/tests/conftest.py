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
def _stage_buckets_without_db(monkeypatch):
    """Stage-move unit tests pass a bare engine object; resolve stage buckets
    with the Python twin of the SQL resolver there (app/core/stage_buckets.py,
    kept in step by tests/test_stage_buckets_twin.py). A real Engine always
    uses the database resolver."""
    from sqlalchemy.engine import Engine

    from app.core.stage_buckets import bucket_for_label
    from app.services import pipeline as pipeline_service

    original = pipeline_service.resolve_application_stage_bucket

    def resolved(engine, application_id, stage):
        if isinstance(engine, Engine):
            return original(engine, application_id, stage)
        return bucket_for_label(stage)

    monkeypatch.setattr(pipeline_service, "resolve_application_stage_bucket", resolved)
    yield


@pytest.fixture(autouse=True)
def _no_archives_without_db(monkeypatch):
    """Unit tests run on MagicMock engines: no candidate is archived there.
    A real Engine always asks dbo.candidate_archives (Phase 4.4)."""
    from sqlalchemy.engine import Engine

    from app.services import candidates as candidate_service

    original = candidate_service.find_open_candidate_archive

    def resolved(engine, candidate_id, tenant_id):
        if isinstance(engine, Engine):
            return original(engine, candidate_id, tenant_id)
        return None

    monkeypatch.setattr(candidate_service, "find_open_candidate_archive", resolved)
    yield


@pytest.fixture(autouse=True)
def _rate_limits_off(monkeypatch):
    """The suite signs in hundreds of times from one client; rate limits are
    exercised explicitly in test_auth_protection.py, which turns them on."""
    from app.core import rate_limit
    from app.core.config import settings

    monkeypatch.setattr(settings, "rate_limit_enabled", False)
    rate_limit.reset_rate_limits()
    yield
    rate_limit.reset_rate_limits()


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
