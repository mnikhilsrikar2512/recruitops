"""Row-level location scoping (pinned list filters + direct-id 404s).

Regression for the Phase 1 live smoke finding: a recruiter listing
/requisitions without location_id saw every location's requisitions, and
GET /requisitions/{id} of another location returned 200.
"""

from types import SimpleNamespace

from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.api import deps
from app.api.v1 import approvals, clients, daily_updates, meetings, requisitions, users
from app.services.auth import AuthContext


def _ctx(role_code: str = "recruiter", location_id: int = 1) -> AuthContext:
    user = SimpleNamespace(id=7, role_code=role_code, location_id=location_id)
    return AuthContext(session_id=1, session_token_hash="token", user=user)


def test_pinned_location_forces_non_admin_to_own_location() -> None:
    assert deps.pinned_location_id(_ctx(location_id=3), None) == 3
    assert deps.pinned_location_id(_ctx(location_id=3), 3) == 3


def test_pinned_location_leaves_admin_filter_alone() -> None:
    assert deps.pinned_location_id(_ctx(role_code="admin"), None) is None
    assert deps.pinned_location_id(_ctx(role_code="admin"), 5) == 5


RECORD_LOCATIONS = {10: 1, 20: 2}


def _load(_engine, record_id: int) -> int:
    if record_id not in RECORD_LOCATIONS:
        raise HTTPException(status_code=404, detail="Thing was not found")
    return RECORD_LOCATIONS[record_id]


def _client(role_code: str, location_id: int = 1) -> TestClient:
    app = FastAPI()
    guard = deps.require_record_in_location("thing_id", _load, "Thing was not found")

    @app.get("/things/{thing_id}")
    def read_thing(thing_id: int, _scope: object = Depends(guard)) -> dict[str, int]:
        return {"id": thing_id}

    app.dependency_overrides[deps.get_current_auth_context] = lambda: _ctx(role_code, location_id)
    app.dependency_overrides[deps.get_engine] = lambda: object()
    return TestClient(app)


def test_record_in_own_location_is_readable() -> None:
    assert _client("recruiter").get("/things/10").status_code == 200


def test_record_in_other_location_is_404_not_403() -> None:
    response = _client("recruiter").get("/things/20")
    assert response.status_code == 404
    assert response.json()["detail"] == "Thing was not found"


def test_missing_record_stays_404() -> None:
    assert _client("recruiter").get("/things/99").status_code == 404


def test_admin_reads_any_location() -> None:
    assert _client("admin").get("/things/20").status_code == 200


def _depends_on(module, endpoint_name: str, guard) -> bool:
    endpoint = getattr(module, endpoint_name)
    defaults = endpoint.__defaults__ or ()
    return any(getattr(d, "dependency", None) is guard for d in defaults)


def test_direct_id_routes_are_guarded() -> None:
    guarded = {
        requisitions: ("_scope_requisition", [
            "get_requisition_detail_endpoint", "update_requisition_endpoint",
            "update_requisition_status_endpoint", "list_requisition_assignments_endpoint",
            "create_requisition_assignment_endpoint", "reassign_requisition_owners_endpoint",
        ]),
        clients: ("_scope_client", [
            "get_client_detail_endpoint", "update_client_endpoint",
            "list_client_contacts_endpoint", "create_client_contact_endpoint",
        ]),
        approvals: ("_scope_approval", ["get_approval_detail_endpoint", "decide_approval_endpoint"]),
        meetings: ("_scope_meeting", ["get_meeting_detail_endpoint", "update_meeting_endpoint"]),
        daily_updates: ("_scope_daily_update", ["get_daily_update_detail_endpoint"]),
        users: ("_scope_user", [
            "get_user_detail_endpoint", "update_user_endpoint", "reset_user_credentials_endpoint",
            "deactivate_user_endpoint", "move_user_endpoint",
        ]),
    }
    missing = [
        f"{module.__name__}.{name}"
        for module, (guard_name, names) in guarded.items()
        for name in names
        if not _depends_on(module, name, getattr(module, guard_name))
    ]
    assert not missing, f"direct-id routes without a location guard: {missing}"
