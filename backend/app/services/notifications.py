from fastapi import HTTPException, status
from sqlalchemy import Engine

from app.repositories.notifications import (
    create_notification,
    find_notification_by_id,
    list_notifications,
    mark_all_notifications_as_read,
    mark_notification_as_read,
    undo_mark_all_notifications_as_read,
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


def mark_all_notifications_read_service(
    engine: Engine,
    auth_context: AuthContext,
) -> dict:
    """Mark all of the current user's unread notifications as read.

    The repository scopes the UPDATE to user_id, so a user can only ever
    clear their own backlog; the return value carries the affected count
    for the confirmation toast.
    """
    updated_ids = mark_all_notifications_as_read(engine, auth_context.user.id)
    return {"updated": len(updated_ids), "notification_ids": updated_ids}


def undo_mark_all_notifications_read_service(
    engine: Engine,
    auth_context: AuthContext,
    notification_ids: list[int],
) -> dict:
    """Revert a mark-all-read batch for the current user.

    The UPDATE is scoped to the owning user, so an id list containing
    someone else's notifications (or an oversized one) simply affects
    fewer rows instead of leaking.
    """
    if not notification_ids:
        return {"reverted": 0}
    reverted_count = undo_mark_all_notifications_as_read(engine, auth_context.user.id, notification_ids)
    return {"reverted": reverted_count}


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
