from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.api import deps
from app.api.deps import get_engine, get_current_auth_context
from app.main import create_application


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
