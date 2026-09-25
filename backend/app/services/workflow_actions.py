from fastapi import HTTPException, status
from sqlalchemy import Engine

from app.repositories.audit import insert_audit_log
from app.repositories.notifications import create_notification
from app.repositories.workflow_actions import (
    create_overlay_submission_event,
    create_workflow_action_event,
    find_workflow_action_item,
    list_workflow_action_items,
    update_workflow_action_status,
)
from app.schemas.notification import NotificationCreate
from app.schemas.pagination import PaginationMeta
from app.schemas.workflow_action import (
    OverlaySubmissionCreate,
    WorkflowActionEventCreate,
    WorkflowActionEventResponse,
    WorkflowActionNudgeRequest,
    WorkflowActionQueueFilters,
    WorkflowActionQueueResponse,
    WorkflowActionResolveRequest,
)
from app.services.auth import AuthContext


def _assert_action_access(auth_context: AuthContext, location_id: int | None, assigned_user_id: int | None) -> None:
    if auth_context.user.role_code == "admin":
        return
    if assigned_user_id == auth_context.user.id:
        return
    if location_id is None:
        return
    if location_id == auth_context.user.location_id:
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Workflow action access is not allowed")


def list_workflow_actions_service(
    engine: Engine,
    auth_context: AuthContext,
    filters: WorkflowActionQueueFilters,
) -> WorkflowActionQueueResponse:
    if auth_context.user.role_code != "admin":
        if filters.location_id and filters.location_id != auth_context.user.location_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Location scope does not allow this action")
        if filters.location_id is None:
            filters = filters.model_copy(update={"location_id": auth_context.user.location_id})

    items, total = list_workflow_action_items(
        engine,
        actor_user_id=auth_context.user.id,
        actor_location_id=auth_context.user.location_id,
        actor_role_code=auth_context.user.role_code,
        is_admin=auth_context.user.role_code == "admin",
        filters=filters,
    )
    return WorkflowActionQueueResponse(
        items=items,
        meta=PaginationMeta(page=filters.page, page_size=filters.page_size, total=total),
    )


def run_workflow_action_service(
    engine: Engine,
    auth_context: AuthContext,
    action_item_id: int,
    payload: WorkflowActionEventCreate,
) -> WorkflowActionEventResponse:
    action_item = find_workflow_action_item(engine, action_item_id)
    if action_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow action was not found")
    _assert_action_access(auth_context, action_item.location_id, action_item.assigned_user_id)

    event_status = "completed" if payload.action_type in {"view", "do_now", "review", "schedule"} else "submitted"
    event = create_workflow_action_event(
        engine,
        action_item_id=action_item.id,
        overlay_key=action_item.overlay_key,
        actor_user_id=auth_context.user.id,
        action_type=payload.action_type,
        event_status=event_status,
        notes=payload.notes,
        payload=payload.payload,
        next_route_href=action_item.route_href,
    )
    if payload.action_type == "do_now" and action_item.status == "open":
        update_workflow_action_status(engine, action_item_id=action_item.id, status="in-progress")
    insert_audit_log(
        engine,
        actor_user_id=auth_context.user.id,
        location_id=action_item.location_id,
        entity_type="workflow_action_item",
        entity_id=action_item.id,
        action_type=f"workflow_action.{payload.action_type}",
        new_values={"event_id": event.id, "payload": payload.payload},
    )
    return WorkflowActionEventResponse.model_validate(event)


def resolve_workflow_action_service(
    engine: Engine,
    auth_context: AuthContext,
    action_item_id: int,
    payload: WorkflowActionResolveRequest,
) -> WorkflowActionEventResponse:
    action_item = find_workflow_action_item(engine, action_item_id)
    if action_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow action was not found")
    _assert_action_access(auth_context, action_item.location_id, action_item.assigned_user_id)

    updated = update_workflow_action_status(engine, action_item_id=action_item.id, status="resolved")
    event = create_workflow_action_event(
        engine,
        action_item_id=action_item.id,
        overlay_key=action_item.overlay_key,
        actor_user_id=auth_context.user.id,
        action_type="resolve",
        event_status="completed",
        notes=payload.resolution_notes,
        payload=payload.payload,
        next_route_href=action_item.route_href,
    )
    insert_audit_log(
        engine,
        actor_user_id=auth_context.user.id,
        location_id=updated.location_id,
        entity_type="workflow_action_item",
        entity_id=updated.id,
        action_type="workflow_action.resolve",
        old_values={"status": action_item.status},
        new_values={"status": updated.status, "event_id": event.id},
    )
    return WorkflowActionEventResponse.model_validate(event)


def nudge_workflow_action_service(
    engine: Engine,
    auth_context: AuthContext,
    action_item_id: int,
    payload: WorkflowActionNudgeRequest,
) -> WorkflowActionEventResponse:
    action_item = find_workflow_action_item(engine, action_item_id)
    if action_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow action was not found")
    _assert_action_access(auth_context, action_item.location_id, action_item.assigned_user_id)

    target_user_id = payload.target_user_id or action_item.assigned_user_id or auth_context.user.id
    message = payload.message or (
        f"Reminder: the action \"{action_item.title}\" on {action_item.entity_type} is still open. "
        "Complete it or pass it on."
    )
    create_notification(
        engine,
        NotificationCreate(
            location_id=action_item.location_id,
            user_id=target_user_id,
            title="Workflow action reminder",
            event_type="workflow_action.nudge",
            source_type=action_item.entity_type,
            source_id=action_item.entity_id or action_item.id,
            message=message,
            priority="normal",
            action_url=action_item.route_href,
        ),
    )
    event = create_workflow_action_event(
        engine,
        action_item_id=action_item.id,
        overlay_key=action_item.overlay_key,
        actor_user_id=auth_context.user.id,
        action_type="nudge",
        event_status="sent",
        notes=payload.message,
        payload={"target_user_id": target_user_id, **payload.payload},
        next_route_href=action_item.route_href,
    )
    insert_audit_log(
        engine,
        actor_user_id=auth_context.user.id,
        location_id=action_item.location_id,
        entity_type="workflow_action_item",
        entity_id=action_item.id,
        action_type="workflow_action.nudge",
        new_values={"target_user_id": target_user_id, "event_id": event.id},
    )
    return WorkflowActionEventResponse.model_validate(event)


def submit_overlay_service(
    engine: Engine,
    auth_context: AuthContext,
    payload: OverlaySubmissionCreate,
) -> WorkflowActionEventResponse:
    action_item = None
    if payload.action_item_id is not None:
        action_item = find_workflow_action_item(engine, payload.action_item_id)
        if action_item is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow action was not found")
        _assert_action_access(auth_context, action_item.location_id, action_item.assigned_user_id)

    event = create_overlay_submission_event(engine, payload=payload, actor_user_id=auth_context.user.id)
    insert_audit_log(
        engine,
        actor_user_id=auth_context.user.id,
        location_id=action_item.location_id if action_item else auth_context.user.location_id,
        entity_type=payload.entity_type,
        entity_id=payload.entity_id or payload.action_item_id or event.id,
        action_type=f"overlay.{payload.action_type}",
        new_values={"overlay_key": payload.overlay_key, "event_id": event.id, "payload": payload.payload},
    )
    return WorkflowActionEventResponse.model_validate(event)
