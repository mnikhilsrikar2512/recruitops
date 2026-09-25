from app.schemas.auth import LoginRequest, ProfileUpdateRequest
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


def test_profile_update_request_requires_a_field() -> None:
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        ProfileUpdateRequest()


def test_profile_update_request_normalizes_name() -> None:
    payload = ProfileUpdateRequest(full_name="  Ada Lovelace  ")
    assert payload.full_name == "Ada Lovelace"


def test_profile_update_request_rejects_whitespace_name() -> None:
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        ProfileUpdateRequest(full_name="   ")


def test_profile_update_request_allows_clearing_phone() -> None:
    payload = ProfileUpdateRequest(phone="   ")
    assert payload.phone is None
    assert "phone" in payload.model_fields_set
