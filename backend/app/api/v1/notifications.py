from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy import Engine

from app.api.deps import get_current_auth_context, get_engine, require_permissions
from app.schemas.notification import (
    NotificationListFilters,
    NotificationListResponse,
    NotificationMarkReadRequest,
    NotificationResponse,
)
from app.services.auth import AuthContext
from app.services.notifications import list_notifications_service, mark_notification_read_service

router = APIRouter(dependencies=[Depends(get_current_auth_context)])


@router.get("/", response_model=NotificationListResponse)
def list_notifications_endpoint(
    _auth: object = Depends(require_permissions("notification.read")),
    status: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    auth_context: AuthContext = Depends(get_current_auth_context),
    engine: Engine = Depends(get_engine),
) -> NotificationListResponse:
    filters = NotificationListFilters(status=status, priority=priority, page=page, page_size=page_size)
    return list_notifications_service(engine, auth_context, filters)


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_read_endpoint(
    payload: NotificationMarkReadRequest,
    _auth: object = Depends(require_permissions("notification.mark_read")),
    notification_id: int = Path(..., ge=1),
    auth_context: AuthContext = Depends(get_current_auth_context),
    engine: Engine = Depends(get_engine),
) -> NotificationResponse:
    _ = payload
    return mark_notification_read_service(engine, auth_context, notification_id)
