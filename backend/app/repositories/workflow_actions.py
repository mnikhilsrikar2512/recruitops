from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import Engine, text

from app.schemas.workflow_action import OverlaySubmissionCreate, WorkflowActionQueueFilters


@dataclass
class WorkflowActionItemRecord:
    id: int
    action_key: str
    source: str
    title: str
    description: str | None
    priority: str
    status: str
    location_id: int | None
    entity_type: str
    entity_id: int | None
    age_label: str | None
    primary_action_label: str
    secondary_action_label: str | None
    route_href: str | None
    overlay_key: str | None
    assigned_user_id: int | None
    assigned_role_code: str | None
    due_at: datetime | None
    resolved_at: datetime | None
    created_at: datetime
    updated_at: datetime


@dataclass
class WorkflowActionEventRecord:
    id: int
    action_item_id: int | None
    overlay_key: str | None
    actor_user_id: int
    action_type: str
    event_status: str
    notes: str | None
    payload: dict[str, Any]
    next_route_href: str | None
    created_at: datetime


def _item_select_sql() -> str:
    return """
        SELECT
          wai.id,
          wai.action_key,
          wai.source,
          wai.title,
          wai.description,
          wai.priority,
          wai.status,
          wai.location_id,
          wai.entity_type,
          wai.entity_id,
          wai.age_label,
          wai.primary_action_label,
          wai.secondary_action_label,
          wai.route_href,
          wai.overlay_key,
          wai.assigned_user_id,
          wai.assigned_role_code,
          wai.due_at,
          wai.resolved_at,
          wai.created_at,
          wai.updated_at
        FROM dbo.workflow_action_items AS wai
    """


def _event_select_sql() -> str:
    return """
        SELECT
          wae.id,
          wae.action_item_id,
          wae.overlay_key,
          wae.actor_user_id,
          wae.action_type,
          wae.event_status,
          wae.notes,
          wae.payload_json,
          wae.next_route_href,
          wae.created_at
        FROM dbo.workflow_action_events AS wae
    """


def _map_event(row) -> WorkflowActionEventRecord:
    payload_json = row["payload_json"]
    payload = json.loads(payload_json) if payload_json else {}
    return WorkflowActionEventRecord(
        id=row["id"],
        action_item_id=row["action_item_id"],
        overlay_key=row["overlay_key"],
        actor_user_id=row["actor_user_id"],
        action_type=row["action_type"],
        event_status=row["event_status"],
        notes=row["notes"],
        payload=payload,
        next_route_href=row["next_route_href"],
        created_at=row["created_at"],
    )


def list_workflow_action_items(
    engine: Engine,
    *,
    actor_user_id: int,
    actor_location_id: int | None,
    actor_role_code: str,
    is_admin: bool,
    filters: WorkflowActionQueueFilters,
) -> tuple[list[WorkflowActionItemRecord], int]:
    query = text(
        f"""
        WITH filtered_actions AS (
          {_item_select_sql()}
          WHERE (:status IS NULL OR wai.status = :status)
          AND (:source IS NULL OR wai.source = :source)
          AND (:location_id IS NULL OR wai.location_id = :location_id)
          AND (
            :is_admin = 1
            OR wai.location_id IS NULL
            OR wai.location_id = :actor_location_id
            OR wai.assigned_user_id = :actor_user_id
            OR wai.assigned_role_code = :actor_role_code
          )
        )
        SELECT *, COUNT(*) OVER() AS total_count
        FROM filtered_actions
        ORDER BY
          CASE priority
            WHEN N'critical' THEN 1
            WHEN N'high' THEN 2
            WHEN N'normal' THEN 3
            ELSE 4
          END,
          COALESCE(due_at, created_at) ASC,
          id ASC
        OFFSET :offset ROWS FETCH NEXT :page_size ROWS ONLY;
        """
    )
    with engine.connect() as connection:
        rows = connection.execute(
            query,
            {
                "status": filters.status,
                "source": filters.source,
                "location_id": filters.location_id,
                "actor_location_id": actor_location_id,
                "actor_user_id": actor_user_id,
                "actor_role_code": actor_role_code,
                "is_admin": 1 if is_admin else 0,
                "offset": (filters.page - 1) * filters.page_size,
                "page_size": filters.page_size,
            },
        ).mappings().all()
    total = rows[0]["total_count"] if rows else 0
    return [WorkflowActionItemRecord(**{key: value for key, value in row.items() if key != "total_count"}) for row in rows], total


def find_workflow_action_item(engine: Engine, action_item_id: int) -> WorkflowActionItemRecord | None:
    query = text(f"{_item_select_sql()} WHERE wai.id = :action_item_id;")
    with engine.connect() as connection:
        row = connection.execute(query, {"action_item_id": action_item_id}).mappings().first()
    return WorkflowActionItemRecord(**row) if row else None


def create_workflow_action_event(
    engine: Engine,
    *,
    action_item_id: int | None,
    overlay_key: str | None,
    actor_user_id: int,
    action_type: str,
    event_status: str,
    notes: str | None,
    payload: dict[str, Any],
    next_route_href: str | None,
) -> WorkflowActionEventRecord:
    query = text(
        """
        INSERT INTO dbo.workflow_action_events (
          action_item_id,
          overlay_key,
          actor_user_id,
          action_type,
          event_status,
          notes,
          payload_json,
          next_route_href,
          created_at
        )
        OUTPUT INSERTED.id
        VALUES (
          :action_item_id,
          :overlay_key,
          :actor_user_id,
          :action_type,
          :event_status,
          :notes,
          :payload_json,
          :next_route_href,
          SYSUTCDATETIME()
        );
        """
    )
    with engine.begin() as connection:
        event_id = connection.execute(
            query,
            {
                "action_item_id": action_item_id,
                "overlay_key": overlay_key,
                "actor_user_id": actor_user_id,
                "action_type": action_type,
                "event_status": event_status,
                "notes": notes,
                "payload_json": json.dumps(payload, default=str),
                "next_route_href": next_route_href,
            },
        ).scalar_one()
    event = find_workflow_action_event(engine, int(event_id))
    if event is None:
        raise RuntimeError("Created workflow action event could not be reloaded")
    return event


def update_workflow_action_status(
    engine: Engine,
    *,
    action_item_id: int,
    status: str,
) -> WorkflowActionItemRecord:
    resolved_at_sql = "SYSUTCDATETIME()" if status in {"resolved", "dismissed", "cancelled"} else "NULL"
    query = text(
        f"""
        UPDATE dbo.workflow_action_items
        SET
          status = :status,
          resolved_at = {resolved_at_sql},
          updated_at = SYSUTCDATETIME()
        WHERE id = :action_item_id;
        """
    )
    with engine.begin() as connection:
        connection.execute(query, {"action_item_id": action_item_id, "status": status})
    updated = find_workflow_action_item(engine, action_item_id)
    if updated is None:
        raise RuntimeError("Updated workflow action item could not be reloaded")
    return updated


def find_workflow_action_event(engine: Engine, event_id: int) -> WorkflowActionEventRecord | None:
    query = text(f"{_event_select_sql()} WHERE wae.id = :event_id;")
    with engine.connect() as connection:
        row = connection.execute(query, {"event_id": event_id}).mappings().first()
    return _map_event(row) if row else None


def create_overlay_submission_event(
    engine: Engine,
    *,
    payload: OverlaySubmissionCreate,
    actor_user_id: int,
) -> WorkflowActionEventRecord:
    event_payload = {
        "parent_route": payload.parent_route,
        "entity_type": payload.entity_type,
        "entity_id": payload.entity_id,
        "form": payload.payload,
    }
    return create_workflow_action_event(
        engine,
        action_item_id=payload.action_item_id,
        overlay_key=payload.overlay_key,
        actor_user_id=actor_user_id,
        action_type=f"overlay.{payload.action_type}",
        event_status="submitted",
        notes=payload.notes,
        payload=event_payload,
        next_route_href=payload.parent_route,
    )
