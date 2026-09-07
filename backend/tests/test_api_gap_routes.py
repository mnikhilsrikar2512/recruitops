from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from app.main import create_application


def test_integrity_error_returns_conflict() -> None:
    app = create_application()

    @app.get("/test-db-conflict")
    def test_db_conflict() -> None:
        raise IntegrityError("INSERT", {}, Exception("Violation of UNIQUE KEY constraint"))

    client = TestClient(app)
    response = client.get("/test-db-conflict")

    assert response.status_code == 409
    assert response.json()["detail"] == "A record with the same unique value already exists"


def test_validation_error_returns_readable_detail() -> None:
    app = create_application()
    client = TestClient(app)

    response = client.post("/api/v1/auth/login", json={"email": "not-an-email", "password": "x"})

    assert response.status_code == 422
    body = response.json()
    assert "detail" in body
    assert "email" in str(body).lower()


def test_application_create_route_is_registered() -> None:
    app = create_application()
    paths = app.openapi()["paths"]
    assert "/api/v1/candidates/{candidate_id}/applications" in paths
    assert "/api/v1/locations/{location_id}" in paths
    assert "/api/v1/roles/{role_id}" in paths
    assert "/api/v1/roles/{role_id}/permissions" in paths
    assert "/api/v1/interviews/" in paths
    assert "/api/v1/interviews/{interview_id}" in paths
    assert "/api/v1/interviews/{interview_id}/feedback" in paths
    assert "/api/v1/offers/" in paths
    assert "/api/v1/offers/{application_id}" in paths
    assert "/api/v1/offers/{application_id}/decision" in paths
    assert "/api/v1/workflow-actions/queue" in paths
    assert "/api/v1/workflow-actions/{action_item_id}/run" in paths
    assert "/api/v1/workflow-actions/{action_item_id}/resolve" in paths
    assert "/api/v1/workflow-actions/{action_item_id}/nudge" in paths
    assert "/api/v1/workflow-actions/overlay-submissions" in paths
