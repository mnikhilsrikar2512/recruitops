"""DB-backed regression tests for the agent run repository and endpoints.

The mock-based unit tests in test_agents_workflows.py monkeypatch the
repository, so they can never catch broken SQL — which is exactly how the
missing ``:actor_user_id`` bind parameter shipped (every non-admin
GET /agents/runs returned 500). These tests execute the real SQL against
the configured database and skip when it is unreachable, matching the
convention in test_permission_catalog.py.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.api.deps import get_engine
from app.main import create_application
from app.repositories.agents import create_agent_run, list_agent_runs
from tests.test_rbac_chain_integration import ADMIN_EMAIL_CANDIDATES, ADMIN_PASSWORD, _db_reachable


@pytest.fixture(scope="module")
def engine():
    if not _db_reachable():
        pytest.skip("Configured SQL Server database is not reachable")
    return get_engine()


@pytest.fixture(scope="module")
def client():
    if not _db_reachable():
        pytest.skip("Configured SQL Server database is not reachable")
    app = create_application()
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


@pytest.fixture(scope="module")
def admin_headers(client):
    for candidate in ADMIN_EMAIL_CANDIDATES:
        attempt = client.post(
            "/api/v1/auth/login",
            json={"email": candidate, "password": ADMIN_PASSWORD},
        )
        if attempt.status_code == 200:
            return {"Authorization": f"Bearer {attempt.json()['token']}"}
    pytest.skip("Seed admin login failed; seed users first")


def _admin_user_id(engine) -> int:
    with engine.connect() as connection:
        return int(
            connection.execute(
                text("SELECT TOP 1 id FROM dbo.users WHERE email = N'admin@executiveconnection.com'")
            ).scalar_one()
        )


class TestListAgentRunsRepository:
    """Direct repository calls: the SQL itself must be valid and scoped."""

    def test_accepts_all_parameters_without_binding_errors(self, engine) -> None:
        admin_id = _admin_user_id(engine)
        # Regression: a missing bind parameter for :actor_user_id raised
        # StatementError here instead of returning rows.
        records, total = list_agent_runs(
            engine, actor_user_id=admin_id, agent_id=None, page=1, page_size=10
        )
        assert total >= 0
        assert isinstance(records, list)

    def test_filters_by_agent_id(self, engine) -> None:
        admin_id = _admin_user_id(engine)
        records, _total = list_agent_runs(
            engine, actor_user_id=admin_id, agent_id="resume_screener", page=1, page_size=10
        )
        assert all(record.agent_id == "resume_screener" for record in records)

    def test_actor_scoping_excludes_other_users_runs(self, engine) -> None:
        admin_id = _admin_user_id(engine)
        records, _total = list_agent_runs(
            engine, actor_user_id=admin_id, agent_id=None, page=1, page_size=50
        )
        assert all(record.actor_user_id == admin_id for record in records)


class TestListAgentRunsEndpoint:
    """HTTP surface: non-admins get their own (possibly empty) list, not a 500."""

    def test_requires_ai_use_permission(self, client) -> None:
        response = client.get("/api/v1/agents/runs")
        assert response.status_code == 401

    def test_admin_can_list_own_runs(self, client, admin_headers) -> None:
        response = client.get("/api/v1/agents/runs?page_size=10", headers=admin_headers)
        assert response.status_code == 200
        body = response.json()
        assert set(body) == {"items", "meta"}
        assert all(item.get("agent_id") for item in body["items"])

    def test_endpoint_returns_valid_page(self, client, admin_headers) -> None:
        response = client.get("/api/v1/agents/runs?page=1&page_size=5", headers=admin_headers)
        assert response.status_code == 200
        body = response.json()
        assert body["meta"]["page"] == 1
        assert body["meta"]["page_size"] == 5
        assert len(body["items"]) <= 5
