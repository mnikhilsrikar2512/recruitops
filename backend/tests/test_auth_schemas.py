from app.schemas.auth import LoginRequest
from app.schemas.permission import PermissionScopePayload, ResolvedPermissionsResponse


def test_login_request_normalizes_email() -> None:
    payload = LoginRequest(email=" TEST@EXAMPLE.COM ", password="x")
    assert payload.email == "test@example.com"


def test_resolved_permissions_response_shape() -> None:
    payload = ResolvedPermissionsResponse(
        role_code="recruiter",
        permissions=["pipeline.read.summary"],
        scopes=PermissionScopePayload(
            clients="location",
            requisitions="location",
            candidates="linked-or-permitted",
            locations="assigned",
            location_ids=[1],
        ),
        allowed_pages=["Pipeline Board"],
    )

    assert payload.role_code == "recruiter"
    assert payload.scopes.location_ids == [1]
