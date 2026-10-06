"""Permission catalog endpoint tests for the role & permissions editor.

The DB-backed tests run against the real configured database and skip when it
is unreachable so the rest of the suite still passes in CI without SQL Server.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import create_application
from tests.test_rbac_chain_integration import ADMIN_EMAIL_CANDIDATES, ADMIN_PASSWORD, _db_reachable


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


def _ai_permission_codes(items: list[dict]) -> set[str]:
    return {item["code"] for item in items if item["code"].startswith("ai.")}


class TestPermissionCatalog:
    def test_catalog_requires_auth(self, client) -> None:
        response = client.get("/api/v1/permissions/")
        assert response.status_code == 401

    def test_catalog_returns_all_permissions(self, client, admin_headers) -> None:
        response = client.get("/api/v1/permissions/", headers=admin_headers)
        assert response.status_code == 200
        items = response.json()["items"]
        assert len(items) >= 60
        assert all({"code", "module_name", "action_name"} <= set(item) for item in items)

    def test_catalog_includes_ai_codes(self, client, admin_headers) -> None:
        response = client.get("/api/v1/permissions/", headers=admin_headers)
        assert response.status_code == 200
        ai_codes = _ai_permission_codes(response.json()["items"])
        assert {"ai.use", "ai.agent.resume_screener", "ai.agent.daily_brief", "ai.agent.inbox_triage"} <= ai_codes

    def test_catalog_groups_under_ai_module(self, client, admin_headers) -> None:
        response = client.get("/api/v1/permissions/", headers=admin_headers)
        assert response.status_code == 200
        ai_items = [item for item in response.json()["items"] if item["module_name"] == "ai"]
        # ai.use + the three agent codes (ai.policy.write is the Admin's governance code, D-03)
        agent_codes = {item["code"] for item in ai_items if item["code"] == "ai.use" or item["code"].startswith("ai.agent.")}
        assert agent_codes == {"ai.use", "ai.agent.daily_brief", "ai.agent.inbox_triage", "ai.agent.resume_screener"}
