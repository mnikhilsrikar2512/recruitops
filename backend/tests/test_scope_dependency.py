from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.api import deps
from app.services.auth import AuthContext


def _build_fake_auth_context(location_id: int = 1) -> AuthContext:
    user = type(
        "FakeUser",
        (),
        {
            "id": 1,
            "role_code": "recruiter",
            "location_id": location_id,
        },
    )()
    return AuthContext(session_id=1, session_token_hash="token", user=user)


def _fake_auth_context_with_location() -> AuthContext:
    return _build_fake_auth_context(1)


def test_location_scope_allows_same_location_query() -> None:
    app = FastAPI()

    @app.get("/guarded")
    async def guarded_route(
        _auth: object = Depends(deps.require_location_scope("location_id")),
    ) -> dict[str, str]:
        return {"status": "ok"}

    app.dependency_overrides[deps.get_current_auth_context] = _fake_auth_context_with_location
    client = TestClient(app)

    response = client.get("/guarded", params={"location_id": 1})
    assert response.status_code == 200


def test_location_scope_blocks_other_location_query() -> None:
    app = FastAPI()

    @app.get("/guarded")
    async def guarded_route(
        _auth: object = Depends(deps.require_location_scope("location_id")),
    ) -> dict[str, str]:
        return {"status": "ok"}

    app.dependency_overrides[deps.get_current_auth_context] = _fake_auth_context_with_location
    client = TestClient(app)

    response = client.get("/guarded", params={"location_id": 2})
    assert response.status_code == 403


def test_location_scope_blocks_other_location_in_body() -> None:
    app = FastAPI()

    @app.post("/guarded")
    async def guarded_route(
        _auth: object = Depends(deps.require_location_scope("location_id")),
    ) -> dict[str, str]:
        return {"status": "ok"}

    app.dependency_overrides[deps.get_current_auth_context] = _fake_auth_context_with_location
    client = TestClient(app)

    response = client.post("/guarded", json={"location_id": 2})
    assert response.status_code == 403
