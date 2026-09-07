from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.schemas.notification import NotificationListFilters
from app.services.auth import AuthContext
from app.services.notifications import list_notifications_service, mark_notification_read_service


def _auth_context(user_id: int, location_id: int | None = 4, role_code: str = "recruiter") -> AuthContext:
    user = SimpleNamespace(id=user_id, location_id=location_id, role_code=role_code)
    return AuthContext(session_id=1, session_token_hash="token", user=user)


def test_list_notifications_uses_current_user_scope(monkeypatch) -> None:
    captured = {}

    def _list_notifications(engine, user_id, filters):
        captured["user_id"] = user_id
        return [], 0

    monkeypatch.setattr("app.services.notifications.list_notifications", _list_notifications)

    response = list_notifications_service(object(), _auth_context(22), NotificationListFilters())

    assert captured["user_id"] == 22
    assert response.meta.total == 0


def test_mark_notification_read_rejects_missing_notification(monkeypatch) -> None:
    monkeypatch.setattr("app.services.notifications.find_notification_by_id", lambda *args, **kwargs: None)

    with pytest.raises(HTTPException) as exc_info:
        mark_notification_read_service(object(), _auth_context(22), 99)

    assert exc_info.value.status_code == 404


def test_mark_notification_read_rejects_other_users_notification(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.notifications.find_notification_by_id",
        lambda *args, **kwargs: SimpleNamespace(id=99, user_id=55),
    )

    with pytest.raises(HTTPException) as exc_info:
        mark_notification_read_service(object(), _auth_context(22), 99)

    assert exc_info.value.status_code == 403


def test_mark_notification_read_succeeds_for_owner(monkeypatch) -> None:
    notification = SimpleNamespace(id=99, user_id=22)
    updated = SimpleNamespace(
        id=99,
        location_id=4,
        user_id=22,
        title="approval_pending",
        message="Review required",
        module_name="approval",
        entity_type="approval",
        entity_id=501,
        priority="high",
        status="read",
        action_url="/approvals/501",
        read_at="2026-08-19T10:00:00Z",
        created_at="2026-08-19T09:00:00Z",
        updated_at="2026-08-19T10:00:00Z",
    )
    monkeypatch.setattr("app.services.notifications.find_notification_by_id", lambda *args, **kwargs: notification)
    monkeypatch.setattr("app.services.notifications.mark_notification_as_read", lambda *args, **kwargs: updated)

    response = mark_notification_read_service(object(), _auth_context(22), 99)

    assert response.id == 99
    assert response.status == "read"
