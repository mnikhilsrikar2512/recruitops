from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.schemas.user import UserMoveRequest
from app.services.auth import AuthContext
from app.services.users import move_user_service


def _auth_context(user_id: int, location_id: int | None, role_code: str = "admin") -> AuthContext:
    user = SimpleNamespace(id=user_id, location_id=location_id, role_code=role_code)
    return AuthContext(session_id=1, session_token_hash="token", user=user)


def _user_record(
    *,
    user_id: int = 22,
    status: str = "active",
    location_id: int = 4,
    role_id: int = 7,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=user_id,
        status=status,
        primary_location_id=location_id,
        primary_role_id=role_id,
        primary_role_code="recruiter",
    )


def test_move_user_requires_review_when_active_work_exists(monkeypatch) -> None:
    monkeypatch.setattr("app.services.users.find_user_by_id", lambda *args, **kwargs: _user_record())
    monkeypatch.setattr("app.services.users.location_exists", lambda *args, **kwargs: True)
    monkeypatch.setattr("app.services.users.role_exists", lambda *args, **kwargs: True)
    monkeypatch.setattr("app.services.users.count_user_active_requisitions", lambda *args, **kwargs: 1)
    monkeypatch.setattr("app.services.users.count_user_active_assignments", lambda *args, **kwargs: 0)
    monkeypatch.setattr("app.services.users.count_user_active_candidate_ownership", lambda *args, **kwargs: 0)
    monkeypatch.setattr("app.services.users.count_user_active_pipeline_ownership", lambda *args, **kwargs: 0)

    with pytest.raises(HTTPException) as exc_info:
        move_user_service(
            object(),
            22,
            UserMoveRequest(new_primary_location_id=8, reason="location split"),
            _auth_context(1, 4),
        )

    assert exc_info.value.status_code == 409
    assert "review confirmation" in exc_info.value.detail


def test_move_user_requires_transfer_when_location_changes_with_active_work(monkeypatch) -> None:
    monkeypatch.setattr("app.services.users.find_user_by_id", lambda *args, **kwargs: _user_record())
    monkeypatch.setattr("app.services.users.location_exists", lambda *args, **kwargs: True)
    monkeypatch.setattr("app.services.users.role_exists", lambda *args, **kwargs: True)
    monkeypatch.setattr("app.services.users.count_user_active_requisitions", lambda *args, **kwargs: 0)
    monkeypatch.setattr("app.services.users.count_user_active_assignments", lambda *args, **kwargs: 2)
    monkeypatch.setattr("app.services.users.count_user_active_candidate_ownership", lambda *args, **kwargs: 0)
    monkeypatch.setattr("app.services.users.count_user_active_pipeline_ownership", lambda *args, **kwargs: 0)

    with pytest.raises(HTTPException) as exc_info:
        move_user_service(
            object(),
            22,
            UserMoveRequest(
                new_primary_location_id=8,
                reason="location split",
                review_confirmed=True,
            ),
            _auth_context(1, 4),
        )

    assert exc_info.value.status_code == 409
    assert "Transfer user is required" in exc_info.value.detail


def test_move_user_allows_role_only_change_without_transfer(monkeypatch) -> None:
    existing = _user_record(role_id=7)
    updated = _user_record(role_id=8)

    monkeypatch.setattr("app.services.users.find_user_by_id", lambda *args, **kwargs: existing)
    monkeypatch.setattr("app.services.users.location_exists", lambda *args, **kwargs: True)
    monkeypatch.setattr("app.services.users.role_exists", lambda *args, **kwargs: True)
    monkeypatch.setattr("app.services.users.count_user_active_requisitions", lambda *args, **kwargs: 0)
    monkeypatch.setattr("app.services.users.count_user_active_assignments", lambda *args, **kwargs: 1)
    monkeypatch.setattr("app.services.users.count_user_active_candidate_ownership", lambda *args, **kwargs: 0)
    monkeypatch.setattr("app.services.users.count_user_active_pipeline_ownership", lambda *args, **kwargs: 0)
    monkeypatch.setattr("app.services.users.transfer_active_user_work_and_move", lambda *args, **kwargs: updated)
    monkeypatch.setattr("app.services.users.insert_audit_log", lambda *args, **kwargs: None)

    response = move_user_service(
        object(),
        22,
        UserMoveRequest(
            new_primary_role_id=8,
            reason="role correction",
            review_confirmed=True,
        ),
        _auth_context(1, 4),
    )

    assert response.new_primary_location_id == 4
    assert response.new_primary_role_id == 8
    assert response.transfer_to_user_id is None
    assert response.review_required is True


def test_move_user_succeeds_with_transfer_and_audit(monkeypatch) -> None:
    existing = _user_record(location_id=4, role_id=7)
    updated = _user_record(location_id=8, role_id=9)
    captured = {}

    def _find_user(engine, user_id):
        if user_id == 22:
            return existing
        if user_id == 30:
            return _user_record(user_id=30, location_id=4, role_id=5)
        return None

    monkeypatch.setattr("app.services.users.find_user_by_id", _find_user)
    monkeypatch.setattr("app.services.users.location_exists", lambda *args, **kwargs: True)
    monkeypatch.setattr("app.services.users.role_exists", lambda *args, **kwargs: True)
    monkeypatch.setattr("app.services.users.count_user_active_requisitions", lambda *args, **kwargs: 1)
    monkeypatch.setattr("app.services.users.count_user_active_assignments", lambda *args, **kwargs: 2)
    monkeypatch.setattr("app.services.users.count_user_active_candidate_ownership", lambda *args, **kwargs: 3)
    monkeypatch.setattr("app.services.users.count_user_active_pipeline_ownership", lambda *args, **kwargs: 4)
    monkeypatch.setattr("app.services.users.transfer_active_user_work_and_move", lambda *args, **kwargs: updated)
    monkeypatch.setattr("app.services.users.insert_audit_log", lambda engine, **kwargs: captured.update(kwargs))

    response = move_user_service(
        object(),
        22,
        UserMoveRequest(
            new_primary_location_id=8,
            new_primary_role_id=9,
            reason="office transfer",
            review_confirmed=True,
            transfer_to_user_id=30,
        ),
        _auth_context(1, 4),
    )

    assert response.previous_primary_location_id == 4
    assert response.new_primary_location_id == 8
    assert response.new_primary_role_id == 9
    assert response.transfer_to_user_id == 30
    assert captured["action_type"] == "moved_with_transfer_review"
    assert captured["new_values"]["active_pipeline_owner_count"] == 4
