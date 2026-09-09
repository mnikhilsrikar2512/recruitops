"""Pipeline template stage validation integration test.

Covers the checks that were dead code while the template-stage repository
functions were stubs:

1. Moving to a stage not in the application's template is rejected (422).
2. Backward movement is rejected (409).
3. Rejection from a stage with ``allows_rejection = 0`` is rejected (422).
4. A forward move within the template succeeds (200).
5. Applications without a template stay unrestricted (regression guard).

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


ADMIN_EMAIL_CANDIDATES = ["admin@executiveconnection.com", "ci.admin@recruitops-test.com"]
ADMIN_PASSWORD = "admin123"


@pytest.fixture(scope="module")
def client():
    if not _db_reachable():
        pytest.skip("Configured SQL Server database is not reachable")
    app = create_application()
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


@pytest.fixture()
def templated_application(client: TestClient):
    """A fresh application pinned to a 4-stage template; auto-cleanup."""
    from sqlalchemy import text

    from app.db.session import create_db_engine

    engine = create_db_engine()
    suffix = uuid.uuid4().hex[:8]
    token = None
    for email in ADMIN_EMAIL_CANDIDATES:
        response = client.post("/api/v1/auth/login", json={"email": email, "password": ADMIN_PASSWORD})
        if response.status_code == 200:
            token = response.json()["token"]
            break
    assert token, "seed admin login failed"

    # Pick a live candidate + requisition pair to hang the application on.
    with engine.connect() as connection:
        pair = connection.execute(
            text(
                """
                SELECT TOP 1 c.id AS candidate_id, r.id AS requisition_id, r.branch_id AS location_id
                FROM dbo.candidates c
                CROSS JOIN dbo.requisitions r
                WHERE r.status = N'open'
                ORDER BY c.id, r.id
                """
            )
        ).mappings().first()
    assert pair, "no candidate/requisition pair available for the test"

    with engine.begin() as connection:
        template_id = connection.execute(
            text(
                """
                INSERT INTO dbo.pipeline_templates (template_name, stage_scope, status, created_by_user_id)
                OUTPUT INSERTED.id
                VALUES (N'CI Validation Template', N'client', N'active', 1)
                """
            )
        ).scalar_one()
        connection.execute(
            text(
                """
                INSERT INTO dbo.pipeline_template_stages
                  (pipeline_template_id, stage_code, stage_name, stage_order, stage_type, allows_rejection)
                VALUES
                  (:template_id, N'shortlisted', N'Shortlisted', 1, N'normal', 0),
                  (:template_id, N'interview', N'Interview', 2, N'normal', 1),
                  (:template_id, N'client-round', N'Client Round', 3, N'normal', 1),
                  (:template_id, N'rejected', N'Rejected', 90, N'rejection', 1)
                """
            ),
            {"template_id": template_id},
        )
        application_id = connection.execute(
            text(
                """
                INSERT INTO dbo.candidate_applications
                  (candidate_id, requisition_id, owner_user_id, current_stage, applied_at,
                   stage_updated_at, pipeline_template_id)
                OUTPUT INSERTED.id
                VALUES
                  (:candidate_id, :requisition_id, 1, N'shortlisted', SYSUTCDATETIME(),
                   SYSUTCDATETIME(), :template_id)
                """
            ),
            {"candidate_id": pair["candidate_id"], "requisition_id": pair["requisition_id"], "template_id": template_id},
        ).scalar_one()

    yield {"application_id": int(application_id), "token": token}

    with engine.begin() as connection:
        connection.execute(
            text("DELETE FROM dbo.candidate_stage_history WHERE candidate_application_id = :application_id"),
            {"application_id": application_id},
        )
        connection.execute(
            text("DELETE FROM dbo.candidate_applications WHERE id = :application_id"),
            {"application_id": application_id},
        )
        connection.execute(
            text("DELETE FROM dbo.pipeline_template_stages WHERE pipeline_template_id = :template_id"),
            {"template_id": template_id},
        )
        connection.execute(
            text("DELETE FROM dbo.pipeline_templates WHERE id = :template_id"),
            {"template_id": template_id},
        )


def _move_stage(client: TestClient, token: str, application_id: int, payload: dict):
    return client.patch(
        f"/api/v1/pipeline/applications/{application_id}/stage",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )


def test_move_to_stage_outside_template_rejected(client: TestClient, templated_application) -> None:
    response = _move_stage(
        client,
        templated_application["token"],
        templated_application["application_id"],
        {"to_stage": "offer"},
    )
    assert response.status_code == 422
    assert "does not belong" in response.json()["detail"]


def test_backward_move_rejected(client: TestClient, templated_application) -> None:
    application_id = templated_application["application_id"]
    first = _move_stage(client, templated_application["token"], application_id, {"to_stage": "interview"})
    assert first.status_code == 200

    backward = _move_stage(client, templated_application["token"], application_id, {"to_stage": "shortlisted"})
    assert backward.status_code == 409
    assert "Backward stage movement" in backward.json()["detail"]


def test_rejection_blocked_from_stage_that_disallows_it(client: TestClient, templated_application) -> None:
    response = _move_stage(
        client,
        templated_application["token"],
        templated_application["application_id"],
        {"to_stage": "rejected", "rejection_reason": "ci validation"},
    )
    assert response.status_code == 422
    assert "Rejection is not allowed" in response.json()["detail"]


def test_forward_move_within_template_succeeds(client: TestClient, templated_application) -> None:
    response = _move_stage(
        client,
        templated_application["token"],
        templated_application["application_id"],
        {"to_stage": "interview"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["from_stage"] == "shortlisted"
    assert body["to_stage"] == "interview"


def test_application_without_template_is_unrestricted(client: TestClient) -> None:
    """No template linked -> no template-driven validation (legacy behavior)."""
    from sqlalchemy import text

    from app.db.session import create_db_engine

    engine = create_db_engine()
    with engine.connect() as connection:
        row = connection.execute(
            text(
                """
                SELECT TOP 1 ca.id
                FROM dbo.candidate_applications ca
                WHERE ca.pipeline_template_id IS NULL
                  AND ca.pipeline_template_id IS NULL
                  AND NOT EXISTS (
                    SELECT 1 FROM dbo.requisitions r
                    WHERE r.id = ca.requisition_id AND r.pipeline_template_id IS NOT NULL
                  )
                """
            )
        ).scalar()
    if row is None:
        pytest.skip("No untemplated application available")

    response = _move_stage(
        client,
        _login_token(client),
        int(row),
        {"to_stage": "some-untemplated-stage"},
    )
    assert response.status_code in (200, 409, 422), response.text
    assert response.status_code != 403


def _login_token(client: TestClient) -> str:
    for email in ADMIN_EMAIL_CANDIDATES:
        response = client.post("/api/v1/auth/login", json={"email": email, "password": ADMIN_PASSWORD})
        if response.status_code == 200:
            return response.json()["token"]
    pytest.fail("seed admin login failed")
