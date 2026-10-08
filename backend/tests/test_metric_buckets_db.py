"""Phase 4.5 exit gate — reports count custom stage labels in the right
metric bucket, and stage history is append-only.

Runs against the configured database (skipped when unreachable). Seeded
rows carry the marker ``MB Gate`` and are removed afterwards.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.db.maintenance import history_maintenance
from app.main import create_application

ADMIN_EMAILS = ["ci.admin@recruitops-test.com", "admin@executiveconnection.com"]
ADMIN_PASSWORD = "admin123"
MARKER = "MB Gate"

# The five non-baseline labels found in live data (readiness Q16) and where
# they must land; plus the baseline aliases the old literal predicates knew.
LIVE_LABELS = {
    "Executive Review": "interview",
    "Technical Interview": "interview",
    "shortlisted": "screened",
    "internal-screening": "screened",
    "some-untemplated-stage": "interview",
    "joined": "joined",
    "hired": "joined",
    "submitted_to_client": "submitted",
    "client-review": "submitted",
    "client-rejected": "rejected",
    "Candidate Withdrawn": "withdrawn",
    "Onboarding": "joined",
}


def _engine():
    from app.db.session import create_db_engine

    return create_db_engine()


def _db_reachable() -> bool:
    try:
        with _engine().connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


@pytest.fixture(scope="module")
def client():
    if not _db_reachable():
        pytest.skip("Configured SQL Server database is not reachable")
    with TestClient(create_application(), raise_server_exceptions=False) as test_client:
        yield test_client


@pytest.fixture(scope="module")
def admin(client):
    for email in ADMIN_EMAILS:
        attempt = client.post("/api/v1/auth/login", json={"email": email, "password": ADMIN_PASSWORD})
        if attempt.status_code == 200 and attempt.json().get("token"):
            with _engine().connect() as connection:
                row = connection.execute(
                    text("SELECT id, tenant_id FROM dbo.users WHERE email = :e"), {"e": email}
                ).mappings().one()
            return {
                "headers": {"Authorization": f"Bearer {attempt.json()['token']}"},
                "user_id": int(row["id"]),
                "tenant_id": int(row["tenant_id"]),
            }
    pytest.fail("No seed admin could log in")


def _cleanup(engine, tenant_id: int) -> None:
    with engine.begin() as connection:
        with history_maintenance(connection):
            connection.execute(text(
                """
                DELETE h FROM dbo.candidate_stage_history AS h
                INNER JOIN dbo.candidate_applications AS ca ON ca.id = h.candidate_application_id
                INNER JOIN dbo.requisitions AS r ON r.id = ca.requisition_id
                WHERE r.title LIKE :m;
                """), {"m": f"{MARKER}%"})
        connection.execute(text(
            """
            DELETE ca FROM dbo.candidate_applications AS ca
            INNER JOIN dbo.requisitions AS r ON r.id = ca.requisition_id
            WHERE r.title LIKE :m;
            """), {"m": f"{MARKER}%"})
        connection.execute(text("DELETE FROM dbo.candidates WHERE full_name LIKE :m"), {"m": f"{MARKER}%"})
        connection.execute(text("DELETE FROM dbo.requisitions WHERE title LIKE :m"), {"m": f"{MARKER}%"})
        connection.execute(text("DELETE FROM dbo.client_companies WHERE name LIKE :m"), {"m": f"{MARKER}%"})
        connection.execute(
            text("DELETE FROM dbo.stage_bucket_map WHERE tenant_id = :t AND stage_key = N'start-date-confirmed'"),
            {"t": tenant_id},
        )


def _seed_application(engine, admin, *, stage: str, suffix: str) -> int:
    with engine.begin() as connection:
        branch_id = connection.execute(
            text("SELECT TOP (1) id FROM dbo.branches WHERE tenant_id = :t ORDER BY id"), {"t": admin["tenant_id"]}
        ).scalar_one()
        client_id = connection.execute(text(
            """
            INSERT INTO dbo.client_companies (branch_id, name, relationship_type, status, placement_fee_pct)
            OUTPUT INSERTED.id VALUES (:b, :n, N'direct-client', N'active', 10)
            """), {"b": branch_id, "n": f"{MARKER} Client {suffix}"}).scalar_one()
        requisition_id = connection.execute(text(
            """
            INSERT INTO dbo.requisitions (branch_id, hiring_type, title, owner_user_id, status, open_positions,
                                          client_company_id, job_description, target_close_date)
            OUTPUT INSERTED.id
            VALUES (:b, N'internal', :t, :u, N'open', 1, :c, N'bucket test',
                    CAST(DATEADD(day, 30, CAST(SYSUTCDATETIME() AS DATE)) AS DATE))
            """), {"b": branch_id, "t": f"{MARKER} Requisition {suffix}", "u": admin["user_id"], "c": client_id}).scalar_one()
        candidate_id = connection.execute(text(
            "INSERT INTO dbo.candidates (full_name, source, created_by_user_id) OUTPUT INSERTED.id VALUES (:n, N'bucket-test', :u)"
        ), {"n": f"{MARKER} Candidate {suffix}", "u": admin["user_id"]}).scalar_one()
        application_id = connection.execute(text(
            """
            INSERT INTO dbo.candidate_applications (candidate_id, requisition_id, owner_user_id, current_stage,
                applied_at, stage_updated_at, offered_ctc, offer_currency)
            OUTPUT INSERTED.id
            VALUES (:c, :r, :u, :s, SYSUTCDATETIME(), SYSUTCDATETIME(), 100000, N'INR')
            """), {"c": candidate_id, "r": requisition_id, "u": admin["user_id"], "s": stage}).scalar_one()
    return int(application_id)


def _add_history(engine, application_id: int, user_id: int, from_stage: str | None, to_stage: str) -> int:
    with engine.begin() as connection:
        connection.execute(text(
            """
            INSERT INTO dbo.candidate_stage_history (candidate_application_id, from_stage, to_stage,
                changed_by_user_id, changed_at, source_type)
            VALUES (:a, :f, :t, :u, SYSUTCDATETIME(), N'manual');
            """), {"a": application_id, "f": from_stage, "t": to_stage, "u": user_id})
        return int(connection.execute(
            text("SELECT MAX(id) FROM dbo.candidate_stage_history WHERE candidate_application_id = :a"),
            {"a": application_id},
        ).scalar_one())


def test_live_labels_resolve_to_the_right_bucket(client):
    with _engine().connect() as connection:
        for label, expected in LIVE_LABELS.items():
            got = connection.execute(text("SELECT dbo.fn_metric_bucket(NULL, NULL, :l)"), {"l": label}).scalar_one()
            assert got == expected, f"{label!r} resolved to {got!r}, expected {expected!r}"


def test_history_snapshots_buckets_and_is_append_only(client, admin):
    engine = _engine()
    _cleanup(engine, admin["tenant_id"])
    try:
        application_id = _seed_application(engine, admin, stage="Technical Interview", suffix="history")
        history_id = _add_history(engine, application_id, admin["user_id"], "shortlisted", "Technical Interview")
        with engine.connect() as connection:
            row = connection.execute(
                text("SELECT from_bucket, to_bucket FROM dbo.candidate_stage_history WHERE id = :id"), {"id": history_id}
            ).mappings().one()
        assert (row["from_bucket"], row["to_bucket"]) == ("screened", "interview")

        with pytest.raises(DBAPIError, match="append-only"):
            with engine.begin() as connection:
                connection.execute(text("UPDATE dbo.candidate_stage_history SET change_reason = N'x' WHERE id = :id"), {"id": history_id})
        with pytest.raises(DBAPIError, match="append-only"):
            with engine.begin() as connection:
                connection.execute(text("UPDATE dbo.candidate_stage_history SET to_bucket = N'joined' WHERE id = :id"), {"id": history_id})
        with pytest.raises(DBAPIError, match="append-only"):
            with engine.begin() as connection:
                connection.execute(text("DELETE FROM dbo.candidate_stage_history WHERE id = :id"), {"id": history_id})

        # The governed maintenance path may delete, and the flag does not
        # outlive the block on the same connection.
        with engine.connect() as connection:
            with connection.begin():
                with history_maintenance(connection):
                    connection.execute(text("DELETE FROM dbo.candidate_stage_history WHERE id = :id"), {"id": history_id})
            flag = connection.execute(text("SELECT CAST(SESSION_CONTEXT(N'recruitops.history_maintenance') AS INT)")).scalar()
            assert flag is None
    finally:
        _cleanup(engine, admin["tenant_id"])


def test_reports_count_custom_joined_labels(client, admin):
    """Exit gate: a company's own 'joined' label counts as a placement, and a
    company mapping changes how a label is counted."""
    engine = _engine()
    _cleanup(engine, admin["tenant_id"])
    try:
        # 'Onboarding' is not a baseline label: the old literal predicate
        # (current_stage IN ('joined','hired')) dropped it from placements.
        onboarding_id = _seed_application(engine, admin, stage="Onboarding", suffix="onboarding")
        _add_history(engine, onboarding_id, admin["user_id"], "offer", "Onboarding")

        # 'Start Date Confirmed' is unknown -> inferred 'interview' until the
        # company maps it to 'joined' on the Stage Bucket Map.
        confirmed_id = _seed_application(engine, admin, stage="Start Date Confirmed", suffix="confirmed")
        listing = client.get("/api/v1/settings/stage-buckets", headers=admin["headers"])
        assert listing.status_code == 200, listing.text
        stage = next(s for s in listing.json()["stages"] if s["stage_key"] == "start-date-confirmed")
        assert (stage["metric_bucket"], stage["source"]) == ("interview", "inferred")

        mapped = client.put(
            "/api/v1/settings/stage-buckets/Start Date Confirmed",
            json={"metric_bucket": "joined"},
            headers=admin["headers"],
        )
        assert mapped.status_code == 200, mapped.text
        assert (mapped.json()["metric_bucket"], mapped.json()["source"]) == ("joined", "company")
        _add_history(engine, confirmed_id, admin["user_id"], "offer", "Start Date Confirmed")

        report = client.get("/api/v1/reports/placements", headers=admin["headers"])
        assert report.status_code == 200, report.text
        names = {r["candidate"] for r in report.json()["rows"]}
        assert f"{MARKER} Candidate onboarding" in names
        assert f"{MARKER} Candidate confirmed" in names

        with engine.connect() as connection:
            audited = connection.execute(text(
                "SELECT COUNT(*) FROM dbo.audit_logs WHERE entity_type = N'stage_bucket_map' AND action_type = N'stage_bucket.set' AND actor_user_id = :u"
            ), {"u": admin["user_id"]}).scalar_one()
        assert audited >= 1

        reset = client.delete("/api/v1/settings/stage-buckets/start-date-confirmed", headers=admin["headers"])
        assert reset.status_code == 200
        assert reset.json()["source"] == "inferred"
    finally:
        _cleanup(engine, admin["tenant_id"])


def test_bad_bucket_is_rejected(client, admin):
    response = client.put(
        "/api/v1/settings/stage-buckets/whatever",
        json={"metric_bucket": "hired"},
        headers=admin["headers"],
    )
    assert response.status_code == 422
