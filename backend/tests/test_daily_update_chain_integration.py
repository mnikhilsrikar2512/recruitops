"""Daily-update chain integration test.

Covers the collaboration chain the assignment fix enables:

    admin creates requisition (owner = admin)
    -> admin assigns recruiter as contributor
    -> recruiter submits a daily update for that requisition
    -> requisition owner receives a notification

The historical bugs this locks down:

1. ``has_user_requisition_link`` only accepted the owner, so assigned
   recruiters could never submit daily updates (403).
2. ``create_requisition_assignment`` overwrote the requisition owner instead
   of inserting an assignment row, so contributor assignment silently stole
   ownership.
3. The daily-update INSERT omitted the NOT NULL ``submitted_at`` column, so
   every submission failed with a misleading 409.

The DB-backed tests run against the real configured database and skip when it
is unreachable so the rest of the suite still passes in CI without SQL Server.
"""
from datetime import date
import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import create_application


# Seed admin candidates: repo dev DB uses the seed user, CI uses the seeded CI admin
ADMIN_EMAIL_CANDIDATES = ["ci.admin@recruitops-test.com", "admin@executiveconnection.com"]
ADMIN_PASSWORD = "admin123"


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
    app = create_application()
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


@pytest.fixture(scope="module")
def daily_chain(client):
    """Set up admin + contributor with daily_update.create_main, once per module."""
    login = None
    for candidate in ADMIN_EMAIL_CANDIDATES:
        attempt = client.post(
            "/api/v1/auth/login",
            json={"email": candidate, "password": ADMIN_PASSWORD},
        )
        if attempt.status_code == 200:
            login = attempt
            break
    if login is None:
        pytest.skip("Seed admin login failed; seed users first")
    admin_headers = {"Authorization": f"Bearer {login.json()['token']}"}
    admin_user_id = login.json()["user"]["id"]

    # Don't assume branch id 1 is the admin's own primary location -- office
    # ids are assigned dynamically (migration 009 made office codes
    # tenant-scoped rather than global), so fetch the admin's real
    # primary_location_id and use it everywhere a location is needed in
    # this fixture/tests, keeping every requisition's location_id and every
    # test user's primary_location_id consistent with _assert_user_in_location.
    admin_detail = client.get(f"/api/v1/users/{admin_user_id}", headers=admin_headers)
    assert admin_detail.status_code == 200, admin_detail.text
    location_id = admin_detail.json()["primary_location_id"]
    assert location_id is not None, "seed admin has no primary_location_id"

    suffix = uuid.uuid4().hex[:8]

    # Don't assume client id 1 exists or belongs to the admin's real
    # location either -- create a client scoped to location_id so the
    # requisitions below satisfy _assert_client_and_contacts' location
    # check, the same way location_id itself was fixed above.
    new_client = client.post(
        "/api/v1/clients/",
        headers=admin_headers,
        json={
            "client_name": f"Daily Chain Client {suffix}",
            "location_id": location_id,
            "client_owner_user_id": admin_user_id,
            "business_source_owner_user_id": admin_user_id,
        },
    )
    assert new_client.status_code == 201, new_client.text
    client_id = new_client.json()["id"]

    role = client.post(
        "/api/v1/roles/",
        headers=admin_headers,
        json={
            "name": f"Daily IT {suffix}",
            "code": f"daily-it-{suffix}",
            "description": "Integration test role for daily-update submissions",
        },
    )
    assert role.status_code == 201, role.text
    role_id = role.json()["id"]

    granted = client.put(
        f"/api/v1/roles/{role_id}/permissions",
        headers=admin_headers,
        json={"permission_codes": ["daily_update.create_main"], "scope_rules": {}},
    )
    assert granted.status_code == 200, granted.text

    user = client.post(
        "/api/v1/users/",
        headers=admin_headers,
        json={
            "full_name": "Daily Integration Recruiter",
            "email": f"daily-it-{suffix}@example.com",
            "employee_code": f"DAILYIT-{suffix}",
            "primary_location_id": location_id,
            "primary_role_id": role_id,
        },
    )
    assert user.status_code == 201, user.text
    user_id = user.json()["id"]

    reset = client.post(
        f"/api/v1/users/{user_id}/credentials/reset",
        headers=admin_headers,
        json={"mode": "setup-link", "issued_by_user_id": admin_user_id},
    )
    assert reset.status_code == 200, reset.text
    setup = client.post(
        "/api/v1/auth/password/setup",
        json={"token": reset.json()["setup_token"], "new_password": "DailyChain123!"},
    )
    assert setup.status_code == 200, setup.text

    user_login = client.post(
        "/api/v1/auth/login",
        json={"email": f"daily-it-{suffix}@example.com", "password": "DailyChain123!"},
    )
    assert user_login.status_code == 200, user_login.text
    user_headers = {"Authorization": f"Bearer {user_login.json()['token']}"}

    yield {
        "admin_headers": admin_headers,
        "admin_user_id": admin_user_id,
        "user_headers": user_headers,
        "user_id": user_id,
        "suffix": suffix,
        "location_id": location_id,
        "client_id": client_id,
    }

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


class TestDailyUpdateChain:
    def test_contributor_assignment_creates_row_without_stealing_ownership(
        self, client, daily_chain
    ):
        requisition = client.post(
            "/api/v1/requisitions/",
            headers=daily_chain["admin_headers"],
            json={
                "client_id": daily_chain["client_id"],
                "location_id": daily_chain["location_id"],
                "title": f"Daily Chain Test {daily_chain['suffix']}",
                "primary_owner_user_id": daily_chain["admin_user_id"],
                "openings_count": 1,
                "priority": "medium",
                "target_closure_date": "2026-12-01",
                "job_description": "Integration test requisition for the daily-update chain",
            },
        )
        assert requisition.status_code == 201, requisition.text
        requisition_id = requisition.json()["id"]

        assignment = client.post(
            f"/api/v1/requisitions/{requisition_id}/assignments",
            headers=daily_chain["admin_headers"],
            json={
                "assigned_user_id": daily_chain["user_id"],
                "assignment_type": "contributor",
            },
        )
        assert assignment.status_code == 201, assignment.text

        owner_after = client.get(
            f"/api/v1/requisitions/{requisition_id}",
            headers=daily_chain["admin_headers"],
        )
        assert owner_after.status_code == 200, owner_after.text
        assert owner_after.json()["primary_owner_user_id"] == daily_chain["admin_user_id"], (
            "contributor assignment must not transfer ownership"
        )

        listed = client.get(
            f"/api/v1/requisitions/{requisition_id}/assignments",
            headers=daily_chain["admin_headers"],
        )
        assert listed.status_code == 200, listed.text
        assignments = listed.json() if isinstance(listed.json(), list) else listed.json().get("items", [])
        assert any(
            a["assigned_user_id"] == daily_chain["user_id"] and a["assignment_type"] == "contributor"
            for a in assignments
        ), "contributor assignment row must exist"

        client.patch(
            f"/api/v1/requisitions/{requisition_id}",
            headers=daily_chain["admin_headers"],
            json={"status": "closed"},
        )

    def test_recruiter_submits_daily_update_and_owner_notified(
        self, client, daily_chain
    ):
        requisition = client.post(
            "/api/v1/requisitions/",
            headers=daily_chain["admin_headers"],
            json={
                "client_id": daily_chain["client_id"],
                "location_id": daily_chain["location_id"],
                "title": f"Daily Submit Test {daily_chain['suffix']}",
                "primary_owner_user_id": daily_chain["admin_user_id"],
                "openings_count": 1,
                "priority": "medium",
                "target_closure_date": "2026-12-01",
                "job_description": "Integration test requisition for daily-update submission",
            },
        )
        assert requisition.status_code == 201, requisition.text
        requisition_id = requisition.json()["id"]

        assignment = client.post(
            f"/api/v1/requisitions/{requisition_id}/assignments",
            headers=daily_chain["admin_headers"],
            json={
                "assigned_user_id": daily_chain["user_id"],
                "assignment_type": "contributor",
            },
        )
        assert assignment.status_code == 201, assignment.text

        submission = client.post(
            "/api/v1/daily-updates/",
            headers=daily_chain["user_headers"],
            json={
                "requisition_id": requisition_id,
                "update_date": date.today().isoformat(),
                "submitted_by_user_id": daily_chain["user_id"],
                "summary": "Contributor daily update submitted through the API chain",
                "submission_status": "submitted",
            },
        )
        assert submission.status_code == 201, submission.text
        update_id = submission.json()["id"]

        notifications = client.get(
            "/api/v1/notifications/?page_size=50",
            headers=daily_chain["admin_headers"],
        )
        assert notifications.status_code == 200, notifications.text
        items = notifications.json().get("items", [])
        owner_notified = any(
            n.get("event_type") == "daily_update_submitted"
            and n.get("source_type") == "daily_update"
            and n.get("source_id") == update_id
            for n in items
        )
        assert owner_notified, (
            "requisition owner must receive a daily_update_submitted notification"
        )

    def test_unlinked_recruiter_cannot_submit(self, client, daily_chain):
        """A user without any link to the requisition is still rejected."""
        requisition = client.post(
            "/api/v1/requisitions/",
            headers=daily_chain["admin_headers"],
            json={
                "client_id": daily_chain["client_id"],
                "location_id": daily_chain["location_id"],
                "title": f"Daily Link Guard {daily_chain['suffix']}",
                "primary_owner_user_id": daily_chain["admin_user_id"],
                "openings_count": 1,
                "priority": "medium",
                "target_closure_date": "2026-12-01",
                "job_description": "Integration test requisition for the link guard",
            },
        )
        assert requisition.status_code == 201, requisition.text
        requisition_id = requisition.json()["id"]

        submission = client.post(
            "/api/v1/daily-updates/",
            headers=daily_chain["user_headers"],
            json={
                "requisition_id": requisition_id,
                "update_date": date.today().isoformat(),
                "submitted_by_user_id": daily_chain["user_id"],
                "summary": "Should be rejected: no assignment, not the owner",
                "submission_status": "submitted",
            },
        )
        assert submission.status_code == 403, submission.text
