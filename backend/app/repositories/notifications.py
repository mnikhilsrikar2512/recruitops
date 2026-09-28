from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import Engine, bindparam, text

from app.schemas.notification import NotificationCreate, NotificationListFilters


@dataclass
class NotificationRecord:
    id: int
    location_id: int | None
    user_id: int
    title: str
    message: str
    module_name: str
    entity_type: str
    entity_id: int
    priority: str
    status: str
    action_url: str | None
    read_at: object
    created_at: object
    updated_at: object
    event_type: str | None
    source_type: str | None
    source_id: int | None


def _notification_select_sql() -> str:
    return """
        SELECT
          n.id,
          n.location_id AS location_id,
          n.user_id,
          n.title,
          n.message,
          n.module_name,
          n.entity_type,
          n.entity_id,
          n.priority,
          n.status,
          n.action_url,
          n.read_at,
          n.created_at,
          n.updated_at,
          n.event_type,
          n.source_type,
          n.source_id
        FROM dbo.notifications AS n
    """


def create_notification(engine: Engine, payload: NotificationCreate) -> NotificationRecord:
    query = text(
        """
        INSERT INTO dbo.notifications (
          location_id, user_id, title, message, module_name, entity_type, entity_id,
          priority, status, action_url, event_type, source_type, source_id
        )
        OUTPUT INSERTED.id
        VALUES (
          :location_id, :user_id, :title, :message, :module_name, :entity_type, :entity_id,
          :priority, N'unread', :action_url, :event_type, :source_type, :source_id
        );
        """
    )
    with engine.begin() as connection:
        notification_id = connection.execute(
            query,
            {
                "location_id": payload.location_id,
                "user_id": payload.user_id,
                "title": (payload.title or payload.message)[:200],
                "message": payload.message,
                "module_name": payload.module_name,
                "entity_type": payload.entity_type,
                "entity_id": payload.entity_id,
                "priority": payload.priority,
                "action_url": payload.action_url,
                "event_type": payload.event_type,
                "source_type": payload.source_type,
                "source_id": payload.source_id,
            },
        ).scalar_one()
    created = find_notification_by_id(engine, int(notification_id))
    if created is None:
        raise RuntimeError("Created notification could not be reloaded")
    return created


def list_notifications(
    engine: Engine,
    user_id: int,
    filters: NotificationListFilters,
) -> tuple[list[NotificationRecord], int]:
    query = text(
        f"""
        WITH filtered_notifications AS (
          {_notification_select_sql()}
          WHERE n.user_id = :user_id
          AND (:status IS NULL OR n.status = :status)
          AND (:priority IS NULL OR n.priority = :priority)
        )
        SELECT *, COUNT(*) OVER() AS total_count
        FROM filtered_notifications
        ORDER BY created_at DESC, id DESC
        OFFSET :offset ROWS FETCH NEXT :page_size ROWS ONLY;
        """
    )
    with engine.connect() as connection:
        rows = connection.execute(
            query,
            {
                "user_id": user_id,
                "status": filters.status,
                "priority": filters.priority,
                "offset": (filters.page - 1) * filters.page_size,
                "page_size": filters.page_size,
            },
        ).mappings().all()
    total = rows[0]["total_count"] if rows else 0
    return [NotificationRecord(**{key: value for key, value in row.items() if key != "total_count"}) for row in rows], total


def find_notification_by_id(engine: Engine, notification_id: int) -> NotificationRecord | None:
    query = text(f"{_notification_select_sql()} WHERE n.id = :notification_id;")
    with engine.connect() as connection:
        row = connection.execute(query, {"notification_id": notification_id}).mappings().first()
    return NotificationRecord(**row) if row else None


def mark_notification_as_read(engine: Engine, notification_id: int) -> NotificationRecord:
    query = text(
        """
        UPDATE dbo.notifications
        SET
          status = N'read',
          read_at = COALESCE(read_at, SYSUTCDATETIME()),
          updated_at = SYSUTCDATETIME()
        WHERE id = :notification_id;
        """
    )
    with engine.begin() as connection:
        connection.execute(query, {"notification_id": notification_id})
    updated = find_notification_by_id(engine, notification_id)
    if updated is None:
        raise RuntimeError("Updated notification could not be reloaded")
    return updated


def mark_all_notifications_as_read(engine: Engine, user_id: int) -> list[int]:
    """Mark every unread notification owned by the user as read.

    Returns the ids of the rows this batch touched so the client can offer
    an exact undo of the whole batch (not just the page it had cached).
    """
    query = text(
        """
        UPDATE dbo.notifications
        SET
          status = N'read',
          read_at = COALESCE(read_at, SYSUTCDATETIME()),
          updated_at = SYSUTCDATETIME()
        OUTPUT INSERTED.id
        WHERE user_id = :user_id AND status = N'unread';
        """
    )
    with engine.begin() as connection:
        rows = connection.execute(query, {"user_id": user_id}).scalars().all()
        return [int(value) for value in rows]


def undo_mark_all_notifications_as_read(engine: Engine, user_id: int, notification_ids: list[int]) -> int:
    """Revert a mark-all-read batch: set the given notifications back to unread.

    Scoped to the owning user and to rows that are currently 'read', so the
    undo can never resurrect older reads or touch another user's rows.
    Returns the affected row count.
    """
    if not notification_ids:
        return 0
    query = text(
        """
        UPDATE dbo.notifications
        SET
          status = N'unread',
          read_at = NULL,
          updated_at = SYSUTCDATETIME()
        WHERE user_id = :user_id AND status = N'read' AND id IN :notification_ids;
        """
    ).bindparams(bindparam("notification_ids", expanding=True))
    with engine.begin() as connection:
        result = connection.execute(query, {"user_id": user_id, "notification_ids": list(notification_ids)})
        return int(result.rowcount or 0)
