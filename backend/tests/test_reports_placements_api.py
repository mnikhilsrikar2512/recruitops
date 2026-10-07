"""Placements + client-summary report integration tests.

Runs against the configured database (skipped gracefully when unreachable),
following the same pattern as test_reports_api.py.

The revenue-math test seeds a self-contained chain (client with fee % ->
requisition -> candidate -> application with CTC -> joined stage history),
asserts the derived revenue exactly, then removes every seeded row so the
run is repeatable. Marker prefix ``RPT Fee Test`` makes leftovers detectable
and deletable on re-runs.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.main import create_application

ADMIN_EMAIL_CANDIDATES = ["admin@executiveconnection.com", "ci.admin@recruitops-test.com"]
ADMIN_PASSWORD = "admin123"
MARKER = "RPT Fee Test"


def _db_reachable() -> bool:
    try:
        from app.db.session import create_db_engine

        engine = create_db_engine()
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def _cleanup(engine) -> None:
    """Delete any leftover marker rows in FK-safe order."""
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                EXEC sp_set_session_context N'recruitops.history_maintenance', 1;
                DELETE h FROM dbo.candidate_stage_history AS h
                INNER JOIN dbo.candidate_applications AS ca ON ca.id = h.candidate_application_id
                INNER JOIN dbo.requisitions AS r ON r.id = ca.requisition_id
                WHERE r.title = :m;
                EXEC sp_set_session_context N'recruitops.history_maintenance', NULL;
                """
            ),
            {"m": f"{MARKER} Requisition"},
        )
        connection.execute(
            text(
                """
                DELETE ca FROM dbo.candidate_applications AS ca
                INNER JOIN dbo.requisitions AS r ON r.id = ca.requisition_id
                WHERE r.title = :m
                """
            ),
            {"m": f"{MARKER} Requisition"},
        )
        connection.execute(
            text("DELETE FROM dbo.candidates WHERE full_name = :m"),
            {"m": f"{MARKER} Candidate"},
        )
        connection.execute(
            text("DELETE FROM dbo.requisitions WHERE title = :m"),
            {"m": f"{MARKER} Requisition"},
        )
        connection.execute(
            text("DELETE FROM dbo.client_companies WHERE name = :m"),
            {"m": f"{MARKER} Client"},
        )


def _seed_revenue_chain(engine) -> tuple[int, float]:
    """Seed client(8.33%) -> requisition -> candidate -> joined application.

    Returns (client_id, expected_revenue).
    """
    ctc = 500000.0
    bonus = 25000.0
    fee_pct = 8.33
    expected_revenue = round((ctc + bonus) * fee_pct / 100.0, 2)

    with engine.begin() as connection:
        branch_id = connection.execute(
            text("SELECT TOP (1) id FROM dbo.branches WHERE status = N'active' ORDER BY id")
        ).scalar_one()
        admin_id = connection.execute(
            text("SELECT TOP (1) id FROM dbo.users WHERE status = N'active' ORDER BY id")
        ).scalar_one()

        client_id = connection.execute(
            text(
                """
                INSERT INTO dbo.client_companies (branch_id, name, relationship_type, status, placement_fee_pct)
                OUTPUT INSERTED.id
                VALUES (:branch_id, :name, N'direct-client', N'active', :fee)
                """
            ),
            {"branch_id": branch_id, "name": f"{MARKER} Client", "fee": fee_pct},
        ).scalar_one()

        requisition_id = connection.execute(
            text(
                """
                INSERT INTO dbo.requisitions (
                    branch_id, hiring_type, title, owner_user_id, status,
                    open_positions, client_company_id, job_description, target_close_date
                )
                OUTPUT INSERTED.id
                VALUES (
                    :branch_id, N'internal', :title, :admin_id, N'open',
                    1, :client_id, N'report test',
                    CAST(DATEADD(day, 30, CAST(SYSUTCDATETIME() AS DATE)) AS DATE)
                )
                """
            ),
            {
                "branch_id": branch_id,
                "title": f"{MARKER} Requisition",
                "admin_id": admin_id,
                "client_id": client_id,
            },
        ).scalar_one()

        candidate_id = connection.execute(
            text(
                """
                INSERT INTO dbo.candidates (full_name, source, created_by_user_id)
                OUTPUT INSERTED.id
                VALUES (:name, N'report-test', :admin_id)
                """
            ),
            {"name": f"{MARKER} Candidate", "admin_id": admin_id},
        ).scalar_one()

        application_id = connection.execute(
            text(
                """
                INSERT INTO dbo.candidate_applications (
                    candidate_id, requisition_id, owner_user_id, current_stage,
                    applied_at, stage_updated_at, offered_ctc, signing_bonus, offer_currency
                )
                OUTPUT INSERTED.id
                VALUES (
                    :candidate_id, :requisition_id, :admin_id, N'joined',
                    SYSUTCDATETIME(), SYSUTCDATETIME(), :ctc, :bonus, N'INR'
                )
                """
            ),
            {
                "candidate_id": candidate_id,
                "requisition_id": requisition_id,
                "admin_id": admin_id,
                "ctc": ctc,
                "bonus": bonus,
            },
        ).scalar_one()

        connection.execute(
            text(
                """
                INSERT INTO dbo.candidate_stage_history (
                    candidate_application_id, from_stage, to_stage,
                    changed_by_user_id, changed_at, source_type
                )
                VALUES (:application_id, N'offered', N'joined', :admin_id, SYSUTCDATETIME(), N'manual')
                """
            ),
            {"application_id": application_id, "admin_id": admin_id},
        )

    return client_id, expected_revenue


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


def test_placements_revenue_math(client, admin_headers):
    from app.db.session import create_db_engine

    engine = create_db_engine()
    _cleanup(engine)
    try:
        _seed_revenue_chain(engine)

        response = client.get(
            "/api/v1/reports/placements", headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()

        # The CI database is shared across tests, so assert on the marker rows
        # rather than the global summary counts.
        marker_rows = [
            r for r in data["rows"] if r["candidate"] == f"{MARKER} Candidate"
        ]
        assert len(marker_rows) == 1
        row = marker_rows[0]
        assert row["client"] == f"{MARKER} Client"
        assert row["fee_pct"] == pytest.approx(8.33)
        assert row["revenue"] == pytest.approx(43732.5)
        assert row["currency"] == "INR"
        assert row["joining_date"] is not None
        assert row["days_to_fill"] is not None

        # Client summary must reconcile with the placements report.
        summary_response = client.get(
            "/api/v1/reports/client-summary", headers=admin_headers
        )
        assert summary_response.status_code == 200
        summary_rows = [
            r
            for r in summary_response.json()["rows"]
            if r["client_name"] == f"{MARKER} Client"
        ]
        assert len(summary_rows) == 1
        summary_row = summary_rows[0]
        assert summary_row["placements"] == 1
        assert summary_row["revenue"] == pytest.approx(43732.5)
        assert summary_row["requisitions"] == 1
        assert summary_row["open_requisitions"] == 1
    finally:
        _cleanup(engine)


def test_placements_period_filter_excludes_other_periods(client, admin_headers):
    """A historical window before any join must return zero seeded rows."""
    response = client.get(
        "/api/v1/reports/placements",
        params={"period_from": "2000-01-01", "period_to": "2000-01-31"},
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["summary"]["placements"] == 0


def test_placements_period_validation(client, admin_headers):
    response = client.get(
        "/api/v1/reports/placements",
        params={"period_from": "2026-09-10", "period_to": "2026-09-01"},
        headers=admin_headers,
    )
    assert response.status_code == 422

    response = client.get(
        "/api/v1/reports/placements",
        params={"period_from": "not-a-date"},
        headers=admin_headers,
    )
    assert response.status_code == 422


def test_reports_require_permission(client):
    """No token -> 401; the permission gate itself is covered by deps tests."""
    response = client.get("/api/v1/reports/placements")
    assert response.status_code == 401
    response = client.get("/api/v1/reports/client-summary")
    assert response.status_code == 401
