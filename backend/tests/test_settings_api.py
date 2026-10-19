"""Company settings API integration tests.

Covers the letterhead source of truth through the real API (skipped
gracefully when the database is unreachable):

1. GET profile returns the primary company entity.
2. PATCH updates profile fields (restores the original values after).
3. PUT logo stores an image; GET /logo serves it without auth; profile
   reports has_logo=true.
4. DELETE clears it; GET /logo then 404s.
5. Invalid logo payload (non-image data URL) is rejected with 422.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.main import create_application

ADMIN_EMAIL_CANDIDATES = ["ci.admin@recruitops-test.com", "admin@executiveconnection.com"]
ADMIN_PASSWORD = "admin123"
TINY_PNG = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


def _db_reachable() -> bool:
    try:
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
    pytest.fail("No seed admin could log in")


def test_get_profile_returns_primary_entity(client, admin_headers):
    response = client.get("/api/v1/settings/profile", headers=admin_headers)
    assert response.status_code == 200
    profile = response.json()
    assert profile["display_name"]
    assert profile["company_code"]
    assert isinstance(profile["has_logo"], bool)


def test_patch_profile_roundtrip(client, admin_headers):
    original = client.get("/api/v1/settings/profile", headers=admin_headers).json()
    try:
        response = client.patch(
            "/api/v1/settings/profile",
            json={"hq_city": "Hyderabad", "support_phone": "+91 40 0000 0000"},
            headers=admin_headers,
        )
        assert response.status_code == 200
        updated = response.json()
        assert updated["hq_city"] == "Hyderabad"
        assert updated["support_phone"] == "+91 40 0000 0000"
    finally:
        restore = {k: original[k] for k in ("hq_city", "support_phone")}
        client.patch("/api/v1/settings/profile", json=restore, headers=admin_headers)


def test_logo_set_serve_clear_cycle(client, admin_headers):
    # Clear first so the cycle starts from a known state. Logos are served per
    # company profile (?v=<profile id>, migration 012).
    client.delete("/api/v1/settings/logo", headers=admin_headers)
    profile_id = client.get("/api/v1/settings/profile", headers=admin_headers).json()["id"]
    logo_path = f"/api/v1/settings/logo?v={profile_id}"
    assert client.get(logo_path).status_code == 404

    put = client.put(
        "/api/v1/settings/logo", json={"data_url": TINY_PNG}, headers=admin_headers
    )
    assert put.status_code == 200
    assert put.json()["logo_url"]

    assert put.json()["logo_url"].endswith(f"v={profile_id}")
    served = client.get(logo_path)
    assert served.status_code == 200
    assert served.headers["content-type"].startswith("image/")
    assert len(served.content) > 0

    profile = client.get("/api/v1/settings/profile", headers=admin_headers).json()
    assert profile["has_logo"] is True

    delete = client.delete("/api/v1/settings/logo", headers=admin_headers)
    assert delete.status_code == 200
    assert delete.json()["logo_url"] is None
    assert client.get(logo_path).status_code == 404


def test_logo_rejects_non_image_payload(client, admin_headers):
    response = client.put(
        "/api/v1/settings/logo",
        json={"data_url": "data:text/html;base64,PGI+aGk8L2I+"},
        headers=admin_headers,
    )
    assert response.status_code == 422


def test_profile_requires_auth(client):
    assert client.get("/api/v1/settings/profile").status_code == 401
    assert client.patch(
        "/api/v1/settings/profile", json={"hq_city": "X"}
    ).status_code == 401
