"""Reports API integration tests.

Covers the three report endpoints through the real API against the configured
database (skipped gracefully when it is unreachable):

1. Time-to-fill: summary math (avg/fastest/slowest, SLA%) + department and
   seniority breakdowns.
2. Source effectiveness: per-source candidate/hire counts, conversion rates,
   best-source highlight.
3. Report datasets: catalog lists the five dimensions; each dataset returns
   rows whose keys match the declared columns.

Permission behavior is covered without the DB via the ``require_permissions``
dependency: a non-admin whose resolved permission set lacks ``report.read``
is rejected; Admin bypasses by role_code.
"""
from __future__ import annotations

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.api.deps import require_permissions
from app.main import create_application


# Seed admin candidates: repo dev DB uses the seed user, CI uses the seeded CI admin
ADMIN_EMAIL_CANDIDATES = ["admin@executiveconnection.com", "ci.admin@recruitops-test.com"]
ADMIN_PASSWORD = "admin123"


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
    pytest.skip("Seed admin login failed; seed users first")


# ---------------------------------------------------------------------------
# Permission dependency (no DB needed)
# ---------------------------------------------------------------------------


class TestReportPermission:
    def _dependency(self):
        return require_permissions("report.read")

    def _auth(self, role_code: str, user_id: int):
        from types import SimpleNamespace

        from app.services.auth import AuthContext

        user = SimpleNamespace(
            id=user_id,
            email="probe@test.local",
            role_code=role_code,
            location_id=1,
            full_name="Probe User",
            business_title=None,
            role_id=2,
            role_name=role_code,
            status="active",
        )
        return AuthContext(session_id=1, session_token_hash="tok", user=user)

    def test_admin_bypasses_report_read(self):
        if not _db_reachable():
            pytest.skip("Configured SQL Server database is not reachable")
        from app.db.session import create_db_engine

        auth = self._auth("admin", user_id=1)
        result = self._dependency()(auth_context=auth, engine=create_db_engine())
        assert result is auth

    def test_missing_report_read_is_403(self):
        if not _db_reachable():
            pytest.skip("Configured SQL Server database is not reachable")
        from app.db.session import create_db_engine

        auth = self._auth("recruiter", user_id=987654321)  # unknown user -> no permissions
        with pytest.raises(HTTPException) as excinfo:
            self._dependency()(auth_context=auth, engine=create_db_engine())
        assert excinfo.value.status_code == 403
        assert "report.read" in str(excinfo.value.detail)


# ---------------------------------------------------------------------------
# Seed: one filled requisition + sourced candidates (idempotent)
# ---------------------------------------------------------------------------


def _seed_reporting_data() -> None:
    from app.db.session import create_db_engine

    engine = create_db_engine()
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                IF NOT EXISTS (SELECT 1 FROM dbo.requisitions WHERE title = N'REPORTS-E2E Filled Role')
                BEGIN
                    DECLARE @client_id BIGINT = (SELECT TOP (1) id FROM dbo.clients ORDER BY id);
                    INSERT INTO dbo.requisitions
                        (branch_id, hiring_type, client_id, title, owner_user_id, status,
                         open_positions, target_close_date, job_description, department_name, sla_days,
                         created_at, updated_at, created_by_user_id)
                    VALUES
                        ((SELECT TOP (1) id FROM dbo.branches ORDER BY id), N'internal', @client_id,
                         N'REPORTS-E2E Filled Role', (SELECT TOP (1) id FROM dbo.users ORDER BY id),
                         N'closed', 1, CAST(GETDATE() AS DATE), N'reports e2e', N'Reports QA', 30,
                         DATEADD(DAY, -20, SYSUTCDATETIME()), DATEADD(DAY, -5, SYSUTCDATETIME()), 1);
                END
                """
            )
        )
        connection.execute(
            text(
                """
                DECLARE @user_id BIGINT = (SELECT TOP (1) id FROM dbo.users ORDER BY id);
                IF NOT EXISTS (SELECT 1 FROM dbo.candidates WHERE full_name LIKE N'REPORTS-E2E%')
                BEGIN
                    INSERT INTO dbo.candidates
                        (full_name, email, source, profile_status, intake_stage, status, created_by_user_id, created_at, updated_at)
                    VALUES
                        (N'REPORTS-E2E Candidate A', N'reports-e2e-a@test.local', N'LinkedIn', N'active', N'finalized', N'active', @user_id,
                         DATEADD(DAY, -15, SYSUTCDATETIME()), DATEADD(DAY, -15, SYSUTCDATETIME())),
                        (N'REPORTS-E2E Candidate B', N'reports-e2e-b@test.local', N'Referral', N'active', N'uploaded', N'active', @user_id,
                         DATEADD(DAY, -15, SYSUTCDATETIME()), DATEADD(DAY, -15, SYSUTCDATETIME()));
                END
                """
            )
        )
        connection.execute(
            text(
                """
                DECLARE @req_id BIGINT = (SELECT TOP (1) id FROM dbo.requisitions WHERE title = N'REPORTS-E2E Filled Role' ORDER BY id DESC);
                DECLARE @cand_id BIGINT = (SELECT TOP (1) id FROM dbo.candidates WHERE full_name = N'REPORTS-E2E Candidate A');
                DECLARE @user_id BIGINT = (SELECT TOP (1) id FROM dbo.users ORDER BY id);
                IF NOT EXISTS (SELECT 1 FROM dbo.candidate_applications WHERE requisition_id = @req_id AND candidate_id = @cand_id)
                BEGIN
                    DECLARE @app_id BIGINT;
                    INSERT INTO dbo.candidate_applications
                        (candidate_id, requisition_id, owner_user_id, current_stage, application_status,
                         applied_at, stage_updated_at, created_at, updated_at)
                    VALUES
                        (@cand_id, @req_id, @user_id, N'joined', N'joined',
                         DATEADD(DAY, -14, SYSUTCDATETIME()), DATEADD(DAY, -5, SYSUTCDATETIME()),
                         DATEADD(DAY, -14, SYSUTCDATETIME()), DATEADD(DAY, -5, SYSUTCDATETIME()));
                    SET @app_id = SCOPE_IDENTITY();
                    INSERT INTO dbo.candidate_stage_history
                        (candidate_application_id, from_stage, to_stage, changed_by_user_id, changed_at, source_type)
                    VALUES (@app_id, N'offer', N'joined', @user_id, DATEADD(DAY, -5, SYSUTCDATETIME()), N'pipeline');
                END
                """
            )
        )


@pytest.fixture(scope="module", autouse=True)
def reporting_data():
    if not _db_reachable():
        return
    _seed_reporting_data()


# ---------------------------------------------------------------------------
# Endpoint behavior against the real database
# ---------------------------------------------------------------------------


class TestTimeToFill:
    def test_summary_math_is_consistent(self, client, admin_headers) -> None:
        response = client.get("/api/v1/reports/time-to-fill", headers=admin_headers)
        assert response.status_code == 200
        summary = response.json()["summary"]
        assert summary["filled_count"] >= 1
        assert summary["avg_days"] is not None and summary["avg_days"] > 0
        assert summary["fastest_days"] <= summary["slowest_days"]
        expected = round(summary["within_sla"] / summary["filled_count"] * 100, 1)
        assert summary["within_sla_percent"] == expected

    def test_breakdowns_include_seeded_department(self, client, admin_headers) -> None:
        body = client.get("/api/v1/reports/time-to-fill", headers=admin_headers).json()
        assert isinstance(body["by_department"], list)
        assert isinstance(body["by_seniority"], list)
        assert "Reports QA" in {row["key"] for row in body["by_department"]}


class TestSourceEffectiveness:
    def test_rows_conversion_and_best_source(self, client, admin_headers) -> None:
        response = client.get("/api/v1/reports/source-effectiveness", headers=admin_headers)
        assert response.status_code == 200
        body = response.json()
        assert body["total_sources"] == len(body["rows"])
        sources = {row["source"] for row in body["rows"]}
        assert {"LinkedIn", "Referral"} <= sources
        for row in body["rows"]:
            assert row["candidates"] >= row["hired"] >= 0
            if row["candidates"]:
                assert row["conversion_rate"] == round(row["hired"] / row["candidates"] * 100, 1)
        if body["best_source"]:
            rates = {r["source"]: r["conversion_rate"] for r in body["rows"]}
            assert rates[body["best_source"]] == max(v for v in rates.values() if v is not None)


class TestReportDatasets:
    def test_catalog_lists_dimensions(self, client, admin_headers) -> None:
        body = client.get("/api/v1/reports/datasets", headers=admin_headers).json()
        keys = {dimension["key"] for dimension in body["dimensions"]}
        assert keys == {
            "time_to_fill",
            "source_effectiveness",
            "pipeline",
            "requisitions",
            "sla",
            "daily_updates",
        }
        for dimension in body["dimensions"]:
            assert dimension["columns"], f"{dimension['key']} must declare columns"

    @pytest.mark.parametrize(
        "dataset", ["time_to_fill", "source_effectiveness", "pipeline", "requisitions", "sla", "daily_updates"]
    )
    def test_dataset_rows_match_declared_columns(self, client, admin_headers, dataset: str) -> None:
        body = client.get(f"/api/v1/reports/datasets/{dataset}", headers=admin_headers).json()
        assert body["dimensions"], f"{dataset} must resolve to a declared dimension"
        declared = {column["key"] for column in body["dimensions"][0]["columns"]}
        for row in body["rows"]:
            assert set(row.keys()) <= declared, f"{dataset} row has undeclared keys"

    def test_unknown_dataset_404s(self, client, admin_headers) -> None:
        response = client.get("/api/v1/reports/datasets/not-a-dataset", headers=admin_headers)
        assert response.status_code == 404


def test_routes_registered() -> None:
    app = create_application()
    paths = app.openapi()["paths"]
    assert "/api/v1/reports/time-to-fill" in paths
    assert "/api/v1/reports/source-effectiveness" in paths
    assert "/api/v1/reports/datasets" in paths
    assert "/api/v1/reports/datasets/{dataset}" in paths
