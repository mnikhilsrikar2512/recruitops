from fastapi import HTTPException, status
from sqlalchemy import Engine

from app.repositories.notifications import (
    create_notification,
    find_notification_by_id,
    list_notifications,
    mark_notification_as_read,
)
from app.schemas.notification import (
    NotificationCreate,
    NotificationListFilters,
    NotificationListResponse,
    NotificationResponse,
)
from app.schemas.pagination import PaginationMeta
from app.services.auth import AuthContext


def create_notification_service(
    engine: Engine,
    payload: NotificationCreate,
) -> NotificationResponse:
    created = create_notification(engine, payload)
    return NotificationResponse.model_validate(created)


def list_notifications_service(
    engine: Engine,
    auth_context: AuthContext,
    filters: NotificationListFilters,
) -> NotificationListResponse:
    items, total = list_notifications(engine, auth_context.user.id, filters)
    return NotificationListResponse(
        items=[NotificationResponse.model_validate(item) for item in items],
        meta=PaginationMeta(page=filters.page, page_size=filters.page_size, total=total),
    )


def mark_notification_read_service(
    engine: Engine,
    auth_context: AuthContext,
    notification_id: int,
) -> NotificationResponse:
    notification = find_notification_by_id(engine, notification_id)
    if not notification:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification was not found")
    if notification.user_id != auth_context.user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Notification access is not allowed")
    updated = mark_notification_as_read(engine, notification_id)
    return NotificationResponse.model_validate(updated)
