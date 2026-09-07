from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_locations_route_requires_auth() -> None:
    response = client.get("/api/v1/locations")
    assert response.status_code == 401


def test_candidates_route_requires_auth() -> None:
    response = client.get("/api/v1/candidates")
    assert response.status_code == 401


def test_requisitions_route_requires_auth() -> None:
    response = client.get("/api/v1/requisitions")
    assert response.status_code == 401
