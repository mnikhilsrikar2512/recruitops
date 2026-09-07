from types import SimpleNamespace

from app.schemas.notification import NotificationCreate
from app.services.notifications import create_notification_service


def test_create_notification_succeeds(monkeypatch) -> None:
    created = SimpleNamespace(
        id=1,
        location_id=4,
        user_id=22,
        title="test_event",
        message="Test notification",
        module_name="test",
        entity_type="test",
        entity_id=100,
        priority="normal",
        status="unread",
        action_url="/test/100",
        read_at=None,
        created_at="2026-08-21T00:00:00Z",
        updated_at="2026-08-21T00:00:00Z",
    )
    monkeypatch.setattr(
        "app.services.notifications.create_notification",
        lambda engine, payload: created,
    )

    response = create_notification_service(
        object(),
        NotificationCreate(
            user_id=22,
            title="test_event",
            message="Test notification",
            module_name="test",
            entity_type="test",
            entity_id=100,
        ),
    )

    assert response.id == 1
    assert response.user_id == 22
    assert response.status == "unread"


def test_create_notification_with_critical_priority(monkeypatch) -> None:
    created = SimpleNamespace(
        id=2,
        location_id=4,
        user_id=22,
        title="critical_event",
        message="Critical alert",
        module_name="pipeline",
        entity_type="pipeline",
        entity_id=200,
        priority="critical",
        status="unread",
        action_url="/pipeline/200",
        read_at=None,
        created_at="2026-08-21T00:00:00Z",
        updated_at="2026-08-21T00:00:00Z",
    )
    monkeypatch.setattr(
        "app.services.notifications.create_notification",
        lambda engine, payload: created,
    )

    response = create_notification_service(
        object(),
        NotificationCreate(
            user_id=22,
            title="critical_event",
            message="Critical alert",
            module_name="pipeline",
            entity_type="pipeline",
            entity_id=200,
            priority="critical",
        ),
    )

    assert response.priority == "critical"
