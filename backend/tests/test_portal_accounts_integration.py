"""Portal accounts API integration test.

Covers the full portal-account surface through the real API:

1. Admin lists accounts (seeded rows are visible with branch/owner joins).
2. Creating a company-shared account works (201) and shows in the list.
3. ``user-owned`` without an owner is rejected (422).
4. Booking a usage slot works (201) with the assigned-user join.
5. Overlapping planned slots are rejected (409).
6. ``end_time <= start_time`` is rejected (422).
7. Patching account status and deleting (cancelling) a slot work.
8. Availability and usage-summary aggregations return entries.

The DB-backed tests run against the real configured database and skip when it
is unreachable so the rest of the suite still passes in CI without SQL Server.
"""
import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import create_application


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


ADMIN_EMAIL_CANDIDATES = ["ci.admin@recruitops-test.com", "admin@executiveconnection.com"]
ADMIN_PASSWORD = "admin123"


@pytest.fixture(scope="module")
def client():
    if not _db_reachable():
        pytest.skip("Configured SQL Server database is not reachable")
    app = create_application()
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


@pytest.fixture()
def admin_headers(client: TestClient):
    token = None
    for email in ADMIN_EMAIL_CANDIDATES:
        response = client.post(
            "/api/v1/auth/login", json={"email": email, "password": ADMIN_PASSWORD}
        )
        if response.status_code == 200:
            token = response.json()["token"]
            break
    assert token, "seed admin login failed"
    return {"Authorization": f"Bearer {token}"}


def _branch_id() -> int:
    from sqlalchemy import text

    from app.db.session import create_db_engine

    engine = create_db_engine()
    with engine.connect() as connection:
        row = connection.execute(text("SELECT TOP 1 id FROM dbo.branches ORDER BY id;")).first()
    assert row, "no branch rows available for the test"
    return int(row[0])


def _any_user_id() -> int:
    from sqlalchemy import text

    from app.db.session import create_db_engine

    engine = create_db_engine()
    with engine.connect() as connection:
        row = connection.execute(
            text("SELECT TOP 1 id FROM dbo.users WHERE status = N'active' ORDER BY id;")
        ).first()
    assert row, "no active users available for the test"
    return int(row[0])


@pytest.fixture()
def scratch_account(client: TestClient, admin_headers):
    """A throwaway portal account; deleted from the DB on teardown."""
    from sqlalchemy import text

    from app.db.session import create_db_engine

    payload = {
        "branch_id": _branch_id(),
        "platform_name": f"CIPlatform-{uuid.uuid4().hex[:6]}",
        "account_name": "CI Shared Account",
        "ownership_type": "company-shared",
        "is_shared": True,
        "has_full_access": False,
        "daily_usage_limit_hours": 2.5,
    }
    response = client.post("/api/v1/portal-accounts/", json=payload, headers=admin_headers)
    assert response.status_code == 201, response.text
    account_id = response.json()["id"]

    yield account_id

    engine = create_db_engine()
    with engine.begin() as connection:
        connection.execute(
            text("DELETE FROM dbo.portal_account_slots WHERE portal_account_id = :id;"),
            {"id": account_id},
        )
        connection.execute(
            text("DELETE FROM dbo.portal_accounts WHERE id = :id;"), {"id": account_id}
        )


def test_list_accounts_includes_seeded_rows(client: TestClient, admin_headers):
    response = client.get("/api/v1/portal-accounts/", headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["meta"]["total"] >= 1
    first = body["items"][0]
    for field in ("platform_name", "account_name", "ownership_type", "status", "branch_name"):
        assert field in first


def test_create_and_show_company_shared_account(
    client: TestClient, admin_headers, scratch_account
):
    detail = client.get(f"/api/v1/portal-accounts/{scratch_account}", headers=admin_headers)
    assert detail.status_code == 200
    body = detail.json()
    assert body["ownership_type"] == "company-shared"
    assert body["daily_usage_limit_hours"] == 2.5
    assert body["branch_name"], "branch join missing"


def test_user_owned_without_owner_rejected(client: TestClient, admin_headers):
    response = client.post(
        "/api/v1/portal-accounts/",
        json={
            "branch_id": _branch_id(),
            "platform_name": "NoOwner",
            "account_name": "Should Fail",
            "ownership_type": "user-owned",
        },
        headers=admin_headers,
    )
    assert response.status_code == 422


def test_slot_booking_overlap_and_validation(
    client: TestClient, admin_headers, scratch_account
):
    user_id = _any_user_id()

    ok = client.post(
        f"/api/v1/portal-accounts/{scratch_account}/slots",
        json={
            "assigned_user_id": user_id,
            "usage_date": "2030-01-15",
            "start_time": "10:00:00",
            "end_time": "12:00:00",
        },
        headers=admin_headers,
    )
    assert ok.status_code == 201, ok.text
    slot = ok.json()
    assert slot["assigned_user_name"], "assigned-user join missing"

    overlap = client.post(
        f"/api/v1/portal-accounts/{scratch_account}/slots",
        json={
            "assigned_user_id": user_id,
            "usage_date": "2030-01-15",
            "start_time": "11:00:00",
            "end_time": "13:00:00",
        },
        headers=admin_headers,
    )
    assert overlap.status_code == 409

    inverted = client.post(
        f"/api/v1/portal-accounts/{scratch_account}/slots",
        json={
            "assigned_user_id": user_id,
            "usage_date": "2030-01-16",
            "start_time": "14:00:00",
            "end_time": "13:00:00",
        },
        headers=admin_headers,
    )
    assert inverted.status_code == 422

    cancel = client.delete(
        f"/api/v1/portal-accounts/{scratch_account}/slots/{slot['id']}",
        headers=admin_headers,
    )
    assert cancel.status_code == 204
    gone = client.get(f"/api/v1/portal-accounts/{scratch_account}/slots", headers=admin_headers)
    assert gone.status_code == 200
    assert all(item["id"] != slot["id"] for item in gone.json()["items"])


def test_patch_account_status(client: TestClient, admin_headers, scratch_account):
    response = client.patch(
        f"/api/v1/portal-accounts/{scratch_account}",
        json={"status": "locked"},
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "locked"


def test_availability_and_usage_summary(client: TestClient, admin_headers):
    availability = client.get(
        "/api/v1/portal-accounts/availability", headers=admin_headers
    )
    assert availability.status_code == 200
    assert isinstance(availability.json()["items"], list)

    summary = client.get("/api/v1/portal-accounts/usage-summary", headers=admin_headers)
    assert summary.status_code == 200
    payload = summary.json()
    assert isinstance(payload["weeks"], list)
    assert isinstance(payload["platforms"], list)
    for entry in payload["platforms"]:
        assert "platform_name" in entry
        assert len(entry["weeks"]) == len(payload["weeks"])
        assert entry["total_hours"] == round(
            sum(bucket["booked_hours"] for bucket in entry["weeks"]), 1
        )

    scoped = client.get(
        "/api/v1/portal-accounts/usage-summary?weeks_back=1", headers=admin_headers
    )
    assert scoped.status_code == 200
    assert len(scoped.json()["weeks"]) <= len(payload["weeks"])


def test_requires_authentication(client: TestClient):
    response = client.get("/api/v1/portal-accounts/")
    assert response.status_code == 401
