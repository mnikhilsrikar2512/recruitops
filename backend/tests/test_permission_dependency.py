from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.api import deps
from app.services.auth import AuthContext


def _fake_auth_context() -> AuthContext:
    user = type(
        "FakeUser",
        (),
        {
            "id": 1,
            "role_code": "recruiter",
            "location_id": 1,
        },
    )()
    return AuthContext(session_id=1, session_token_hash="token", user=user)


def _fake_engine() -> object:
    return object()


def test_require_permissions_blocks_when_permission_missing(monkeypatch) -> None:
    app = FastAPI()

    @app.get("/guarded")
    def guarded_route(
        _auth: object = Depends(deps.require_permissions("location.read")),
    ) -> dict[str, str]:
        return {"status": "ok"}

    app.dependency_overrides[deps.get_current_auth_context] = _fake_auth_context
    app.dependency_overrides[deps.get_engine] = _fake_engine
    monkeypatch.setattr(deps, "list_resolved_permissions", lambda engine, user_id: [])

    client = TestClient(app)
    response = client.get("/guarded")

    assert response.status_code == 403


def test_require_permissions_allows_when_permission_present(monkeypatch) -> None:
    app = FastAPI()

    @app.get("/guarded")
    def guarded_route(
        _auth: object = Depends(deps.require_permissions("location.read")),
    ) -> dict[str, str]:
        return {"status": "ok"}

    app.dependency_overrides[deps.get_current_auth_context] = _fake_auth_context
    app.dependency_overrides[deps.get_engine] = _fake_engine
    monkeypatch.setattr(deps, "list_resolved_permissions", lambda engine, user_id: ["location.read"])

    client = TestClient(app)
    response = client.get("/guarded")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_require_any_permission_allows_when_one_permission_matches(monkeypatch) -> None:
    app = FastAPI()

    @app.get("/guarded")
    def guarded_route(
        _auth: object = Depends(
            deps.require_any_permission(
                "candidate.duplicate.request_override",
                "candidate.duplicate.link_existing",
            )
        ),
    ) -> dict[str, str]:
        return {"status": "ok"}

    app.dependency_overrides[deps.get_current_auth_context] = _fake_auth_context
    app.dependency_overrides[deps.get_engine] = _fake_engine
    monkeypatch.setattr(deps, "list_resolved_permissions", lambda engine, user_id: ["candidate.duplicate.link_existing"])

    client = TestClient(app)
    response = client.get("/guarded")

    assert response.status_code == 200
