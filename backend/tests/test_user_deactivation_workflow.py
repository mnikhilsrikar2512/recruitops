from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.schemas.user import UserDeactivateRequest
from app.services.auth import AuthContext
from app.services.users import deactivate_user_service


def _auth_context(user_id: int, location_id: int | None, role_code: str = "admin") -> AuthContext:
    user = SimpleNamespace(id=user_id, location_id=location_id, role_code=role_code)
    return AuthContext(session_id=1, session_token_hash="token", user=user)


def _user_record(status: str = "active", location_id: int = 4) -> SimpleNamespace:
    return SimpleNamespace(
        id=22,
        status=status,
        primary_location_id=location_id,
    )


def test_deactivate_user_requires_review_when_active_work_exists(monkeypatch) -> None:
    monkeypatch.setattr("app.services.users.find_user_by_id", lambda *args, **kwargs: _user_record())
    monkeypatch.setattr("app.services.users.count_user_active_requisitions", lambda *args, **kwargs: 1)
    monkeypatch.setattr("app.services.users.count_user_active_assignments", lambda *args, **kwargs: 0)
    monkeypatch.setattr("app.services.users.count_user_active_candidate_ownership", lambda *args, **kwargs: 0)
    monkeypatch.setattr("app.services.users.count_user_active_pipeline_ownership", lambda *args, **kwargs: 0)

    with pytest.raises(HTTPException) as exc_info:
        deactivate_user_service(object(), 22, UserDeactivateRequest(reason="leaving"), _auth_context(1, 4))

    assert exc_info.value.status_code == 409


def test_deactivate_user_requires_transfer_target_when_active_work_exists(monkeypatch) -> None:
    monkeypatch.setattr("app.services.users.find_user_by_id", lambda *args, **kwargs: _user_record())
    monkeypatch.setattr("app.services.users.count_user_active_requisitions", lambda *args, **kwargs: 0)
    monkeypatch.setattr("app.services.users.count_user_active_assignments", lambda *args, **kwargs: 1)
    monkeypatch.setattr("app.services.users.count_user_active_candidate_ownership", lambda *args, **kwargs: 0)
    monkeypatch.setattr("app.services.users.count_user_active_pipeline_ownership", lambda *args, **kwargs: 0)

    with pytest.raises(HTTPException) as exc_info:
        deactivate_user_service(
            object(),
            22,
            UserDeactivateRequest(reason="leaving", review_confirmed=True),
            _auth_context(1, 4),
        )

    assert exc_info.value.status_code == 409


def test_deactivate_user_succeeds_with_transfer_and_audit(monkeypatch) -> None:
    existing = _user_record()
    updated = SimpleNamespace(status="inactive")
    captured = {}
    monkeypatch.setattr(
        "app.services.users.find_user_by_id",
        lambda engine, user_id: existing if user_id == 22 else SimpleNamespace(id=30, status="active", primary_location_id=4),
    )
    monkeypatch.setattr("app.services.users.count_user_active_requisitions", lambda *args, **kwargs: 1)
    monkeypatch.setattr("app.services.users.count_user_active_assignments", lambda *args, **kwargs: 2)
    monkeypatch.setattr("app.services.users.count_user_active_candidate_ownership", lambda *args, **kwargs: 3)
    monkeypatch.setattr("app.services.users.count_user_active_pipeline_ownership", lambda *args, **kwargs: 4)
    monkeypatch.setattr("app.services.users.transfer_active_user_work_and_deactivate", lambda *args, **kwargs: updated)
    monkeypatch.setattr("app.services.users.insert_audit_log", lambda engine, **kwargs: captured.update(kwargs))

    response = deactivate_user_service(
        object(),
        22,
        UserDeactivateRequest(
            reason="leaving",
            review_confirmed=True,
            transfer_to_user_id=30,
        ),
        _auth_context(1, 4),
    )

    assert response.new_status == "inactive"
    assert response.transfer_to_user_id == 30
    assert captured["action_type"] == "deactivated_with_transfer"
    assert captured["new_values"]["active_pipeline_owner_count"] == 4
