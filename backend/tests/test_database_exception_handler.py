from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.main import create_application


def test_operational_error_returns_service_unavailable() -> None:
    app = create_application()

    @app.get("/test-db-unavailable")
    def test_db_unavailable() -> None:
        raise OperationalError("SELECT 1", {}, Exception("Login timeout expired"))

    client = TestClient(app)

    response = client.get("/test-db-unavailable")

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Database is currently unavailable. Please restore SQL Server connectivity and try again."
    }
