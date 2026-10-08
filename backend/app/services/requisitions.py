from fastapi import HTTPException, status
from sqlalchemy import Engine
from app.repositories.versioning import StaleWriteConflict

from app.repositories.clients import find_client_by_id, list_client_contacts
from app.repositories.audit import insert_audit_log
from app.repositories.requisitions import (
    count_active_requisition_applications,
    count_active_requisition_assignments,
    create_requisition,
    create_requisition_assignment,
    find_requisition_assignment_by_id,
    find_requisition_by_id,
    list_requisition_assignments,
    list_requisitions,
    remove_requisition_assignment,
    update_requisition,
    update_requisition_status,
)
from app.repositories.requisition_holds import find_open_hold, hold_impact, list_holds, put_on_hold, resume_from_hold
from app.repositories.stage_lists import point_requisition_at_list
from app.repositories.users import find_user_by_id
from app.schemas.notification import NotificationCreate
from app.schemas.pagination import PaginationMeta
from app.schemas.requisition import (
    RequisitionAssignmentCreate,
    RequisitionAssignmentResponse,
    RequisitionCreate,
    RequisitionListFilters,
    RequisitionListResponse,
    RequisitionResponse,
    RequisitionOwnerReassignment,
    RequisitionOwnerReassignmentResponse,
    RequisitionHoldCreate,
    RequisitionHoldResponse,
    RequisitionResume,
    RequisitionStatusUpdate,
    RequisitionUpdate,
)
from app.core.withdrawal import HOLD_REASON_LABELS
from app.services.auth import AuthContext
from app.services.notifications import create_notification_service


def _assert_user_in_location(engine: Engine, user_id: int, location_id: int, label: str) -> None:
    user = find_user_by_id(engine, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{label} was not found")
    if user.primary_location_id != location_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{label} must belong to the same location",
        )


def _assert_client_and_contacts(
    engine: Engine,
    client_id: int,
    location_id: int,
    primary_contact_id: int | None,
    secondary_contact_id: int | None,
) -> None:
    client = find_client_by_id(engine, client_id)
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client was not found")
    if getattr(client, "archived_at", None) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This client is archived; restore it first")
    if client.location_id != location_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Client must belong to the same location",
        )
    if client.status != "active":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only active clients can be used for requisitions",
        )
    contacts = list_client_contacts(engine, client_id)
    if primary_contact_id and not any(contact.id == primary_contact_id for contact in contacts):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Primary contact must belong to the selected client",
        )
    if secondary_contact_id and not any(contact.id == secondary_contact_id for contact in contacts):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Secondary contact must belong to the selected client",
        )


def list_requisitions_service(engine: Engine, filters: RequisitionListFilters) -> RequisitionListResponse:
    items, total = list_requisitions(engine, filters)
    return RequisitionListResponse(
        items=[RequisitionResponse.model_validate(item) for item in items],
        meta=PaginationMeta(page=filters.page, page_size=filters.page_size, total=total),
    )


def create_requisition_service(engine: Engine, payload: RequisitionCreate) -> RequisitionResponse:
    _assert_client_and_contacts(
        engine,
        client_id=payload.client_id,
        location_id=payload.location_id,
        primary_contact_id=payload.primary_contact_id,
        secondary_contact_id=payload.secondary_contact_id,
    )
    _assert_user_in_location(engine, payload.primary_owner_user_id, payload.location_id, "Primary owner user")
    if payload.delivery_owner_user_id:
        _assert_user_in_location(engine, payload.delivery_owner_user_id, payload.location_id, "Delivery owner user")
    created = create_requisition(engine, payload)
    # Phase 4.10: the requisition follows its client's stage list (or the
    # company default); a per-requisition choice is not offered.
    if isinstance(engine, Engine):
        try:
            point_requisition_at_list(engine, created.id)
            created = find_requisition_by_id(engine, created.id) or created
        except Exception:  # noqa: BLE001 - stage lists are optional; never block intake
            pass
    try:
        create_notification_service(
            engine,
            NotificationCreate(
                location_id=payload.location_id,
                user_id=payload.primary_owner_user_id,
                event_type="requisition_created",
                source_type="requisition",
                source_id=created.id,
                title="You are the primary owner of a new requisition",
                message=(
                    f"{created.title}{' for ' + created.client_name if created.client_name else ''} "
                    "was created and assigned to you. Review intake and start sourcing."
                ),
                priority="normal",
                action_url=f"/requisitions/{created.id}",
            ),
        )
    except Exception:
        pass
    return RequisitionResponse.model_validate(created)


def get_requisition_detail_service(engine: Engine, requisition_id: int) -> RequisitionResponse:
    requisition = find_requisition_by_id(engine, requisition_id)
    if not requisition:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Requisition was not found")
    response = RequisitionResponse.model_validate(requisition)
    if response.status == "on-hold":
        hold = find_open_hold(engine, requisition_id)
        if hold:
            response.active_hold = _hold_response(hold).model_dump(mode="json")
    return response


def _hold_response(row: dict) -> RequisitionHoldResponse:
    return RequisitionHoldResponse(**row, reason_label=HOLD_REASON_LABELS.get(row["reason_code"], row["reason_code"]))


def update_requisition_service(engine: Engine, requisition_id: int, payload: RequisitionUpdate) -> RequisitionResponse:
    existing = find_requisition_by_id(engine, requisition_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Requisition was not found")
    _assert_client_and_contacts(
        engine,
        client_id=existing.client_id or 0,
        location_id=existing.location_id,
        primary_contact_id=payload.primary_contact_id if "primary_contact_id" in payload.model_fields_set else existing.primary_contact_id,
        secondary_contact_id=payload.secondary_contact_id if "secondary_contact_id" in payload.model_fields_set else existing.secondary_contact_id,
    )
    if payload.primary_owner_user_id:
        _assert_user_in_location(engine, payload.primary_owner_user_id, existing.location_id, "Primary owner user")
    if payload.delivery_owner_user_id:
        _assert_user_in_location(engine, payload.delivery_owner_user_id, existing.location_id, "Delivery owner user")
    try:
        updated = update_requisition(engine, requisition_id, payload)
    except StaleWriteConflict as conflict:
        conflict.current = get_requisition_detail_service(engine, requisition_id)
        raise
    return RequisitionResponse.model_validate(updated)


def update_requisition_status_service(
    engine: Engine,
    requisition_id: int,
    payload: RequisitionStatusUpdate,
    auth_context: AuthContext | None = None,
) -> RequisitionResponse:
    existing = find_requisition_by_id(engine, requisition_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Requisition was not found")
    actor_user_id = auth_context.user.id if auth_context else existing.primary_owner_user_id
    try:
        # Phase 4.12: moving in or out of on-hold goes through the hold flow
        # so the hold is recorded and the clocks pause.
        if payload.status == "on-hold" and existing.status != "on-hold":
            put_on_hold(engine, requisition_id, reason_code="other", reason_note=payload.reason,
                        expected_resume_date=None, user_id=actor_user_id, version=payload.version)
            updated = find_requisition_by_id(engine, requisition_id)
        elif existing.status == "on-hold" and payload.status != "on-hold":
            resume_from_hold(engine, requisition_id, user_id=actor_user_id, note=payload.reason,
                             to_status=payload.status, version=payload.version)
            updated = find_requisition_by_id(engine, requisition_id)
        else:
            updated = update_requisition_status(engine, requisition_id, payload)
    except StaleWriteConflict as conflict:
        conflict.current = get_requisition_detail_service(engine, requisition_id)
        raise
    if getattr(existing, "primary_owner_user_id", None):
        try:
            create_notification_service(
                engine,
                NotificationCreate(
                    location_id=existing.location_id,
                    user_id=existing.primary_owner_user_id,
                    event_type="requisition_status_changed",
                    source_type="requisition",
                    source_id=requisition_id,
                    title="Requisition status changed",
                    message=(
                        f"{existing.title} moved from {existing.status} to {payload.status}. "
                        "Open the requisition to see what this changes for your pipeline."
                    ),
                    priority="normal",
                    action_url=f"/requisitions/{requisition_id}",
                ),
            )
        except Exception:
            pass
    if auth_context:
        insert_audit_log(
            engine,
            actor_user_id=auth_context.user.id,
            location_id=auth_context.user.location_id,
            entity_type="requisition",
            entity_id=requisition_id,
            action_type="status_updated",
            old_values={"status": existing.status},
            new_values={"status": payload.status, "reason": payload.reason},
        )
    return RequisitionResponse.model_validate(updated)


def list_requisition_assignments_service(engine: Engine, requisition_id: int) -> list[RequisitionAssignmentResponse]:
    existing = find_requisition_by_id(engine, requisition_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Requisition was not found")
    items = list_requisition_assignments(engine, requisition_id)
    return [RequisitionAssignmentResponse.model_validate(item) for item in items]


def create_requisition_assignment_service(
    engine: Engine,
    requisition_id: int,
    payload: RequisitionAssignmentCreate,
) -> RequisitionAssignmentResponse:
    existing = find_requisition_by_id(engine, requisition_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Requisition was not found")
    _assert_user_in_location(engine, payload.assigned_user_id, existing.location_id, "Assigned user")
    created = create_requisition_assignment(engine, existing.location_id, requisition_id, payload)
    try:
        create_notification_service(
            engine,
            NotificationCreate(
                location_id=existing.location_id,
                user_id=payload.assigned_user_id,
                event_type="requisition_assigned",
                source_type="requisition",
                source_id=requisition_id,
                title="You were added to a requisition",
                message=(
                    f"You have been added as an assignee on {existing.title}. "
                    "Open the requisition to see what you now own."
                ),
                priority="normal",
                action_url=f"/requisitions/{requisition_id}",
            ),
        )
    except Exception:
        pass
    return RequisitionAssignmentResponse.model_validate(created)


def remove_requisition_assignment_service(engine: Engine, assignment_id: int) -> dict[str, object]:
    assignment = find_requisition_assignment_by_id(engine, assignment_id)
    if not assignment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Requisition assignment was not found")
    remove_requisition_assignment(engine, assignment_id)
    return {"assignment_id": assignment_id, "status": "removed"}


def reassign_requisition_owners_service(
    engine: Engine,
    requisition_id: int,
    payload: RequisitionOwnerReassignment,
    auth_context: AuthContext | None = None,
) -> RequisitionOwnerReassignmentResponse:
    existing = find_requisition_by_id(engine, requisition_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Requisition was not found")

    next_primary_owner_user_id = payload.new_primary_owner_user_id or existing.primary_owner_user_id
    next_delivery_owner_user_id = (
        payload.new_delivery_owner_user_id
        if "new_delivery_owner_user_id" in payload.model_fields_set
        else existing.delivery_owner_user_id
    )

    _assert_user_in_location(engine, next_primary_owner_user_id, existing.location_id, "Primary owner user")
    if next_delivery_owner_user_id is not None:
        _assert_user_in_location(engine, next_delivery_owner_user_id, existing.location_id, "Delivery owner user")

    active_assignment_count = count_active_requisition_assignments(engine, requisition_id)
    active_application_count = count_active_requisition_applications(engine, requisition_id)
    review_required = active_assignment_count > 0 or active_application_count > 0
    if review_required and not payload.review_confirmed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Owner reassignment requires active-work review confirmation",
        )

    update_requisition(
        engine,
        requisition_id,
        RequisitionUpdate(
            primary_owner_user_id=next_primary_owner_user_id,
            delivery_owner_user_id=next_delivery_owner_user_id,
        ),
    )
    try:
        create_notification_service(
            engine,
            NotificationCreate(
                location_id=existing.location_id,
                user_id=next_primary_owner_user_id,
                event_type="requisition_owner_reassigned",
                source_type="requisition",
                source_id=requisition_id,
                title="You are now the requisition owner",
                message=(
                    f"You are now the primary owner of {existing.title}. "
                    "Open it to review and prioritize the work."
                ),
                priority="normal",
                action_url=f"/requisitions/{requisition_id}",
            ),
        )
    except Exception:
        pass
    actor_user_id = payload.changed_by_user_id or (auth_context.user.id if auth_context else None)
    if actor_user_id is not None:
        insert_audit_log(
            engine,
            actor_user_id=actor_user_id,
            location_id=existing.location_id,
            entity_type="requisition",
            entity_id=requisition_id,
            action_type="owners_reassigned",
            old_values={
                "primary_owner_user_id": existing.primary_owner_user_id,
                "delivery_owner_user_id": existing.delivery_owner_user_id,
            },
            new_values={
                "primary_owner_user_id": next_primary_owner_user_id,
                "delivery_owner_user_id": next_delivery_owner_user_id,
                "reason": payload.reason,
                "review_confirmed": payload.review_confirmed,
                "active_assignment_count": active_assignment_count,
                "active_application_count": active_application_count,
            },
        )
    return RequisitionOwnerReassignmentResponse(
        requisition_id=requisition_id,
        previous_primary_owner_user_id=existing.primary_owner_user_id,
        new_primary_owner_user_id=next_primary_owner_user_id,
        previous_delivery_owner_user_id=existing.delivery_owner_user_id,
        new_delivery_owner_user_id=next_delivery_owner_user_id,
        active_assignment_count=active_assignment_count,
        active_application_count=active_application_count,
        review_required=review_required,
        reason=payload.reason,
    )


# ---- Phase 4.12 (D-4.12): client puts a requisition on hold -------------
def hold_requisition_service(
    engine: Engine,
    requisition_id: int,
    payload: RequisitionHoldCreate,
    auth_context: AuthContext,
) -> RequisitionResponse:
    existing = find_requisition_by_id(engine, requisition_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Requisition was not found")
    if existing.status == "on-hold":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This requisition is already on hold")
    if existing.status in ("closed", "cancelled"):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"A {existing.status} requisition can't be put on hold")
    try:
        put_on_hold(engine, requisition_id, reason_code=payload.reason_code, reason_note=payload.note,
                    expected_resume_date=payload.expected_resume_date, user_id=auth_context.user.id,
                    version=payload.version)
    except StaleWriteConflict as conflict:
        conflict.current = get_requisition_detail_service(engine, requisition_id)
        raise
    impact = hold_impact(engine, requisition_id)
    label = HOLD_REASON_LABELS.get(payload.reason_code, payload.reason_code)
    recipients = set(impact["owner_user_ids"])
    if existing.primary_owner_user_id:
        recipients.add(existing.primary_owner_user_id)
    interviews = impact["upcoming_interviews"]
    for user_id in recipients:
        try:
            create_notification_service(
                engine,
                NotificationCreate(
                    location_id=existing.location_id,
                    user_id=user_id,
                    event_type="requisition_on_hold",
                    source_type="requisition",
                    source_id=requisition_id,
                    title="Requisition put on hold",
                    message=(
                        f"{existing.title} is on hold ({label}). Candidates stay where they are; "
                        + (f"{interviews} scheduled interview(s) need you to tell the candidates or reschedule. "
                           if interviews else "")
                        + "You can still withdraw or reject a candidate."
                    ),
                    priority="high" if interviews else "normal",
                    action_url=f"/requisitions/{requisition_id}",
                ),
            )
        except Exception:
            pass
    insert_audit_log(
        engine,
        actor_user_id=auth_context.user.id,
        location_id=auth_context.user.location_id,
        entity_type="requisition",
        entity_id=requisition_id,
        action_type="requisition.hold",
        old_values={"status": existing.status},
        new_values={"status": "on-hold", "reason_code": payload.reason_code, "note": payload.note,
                    "expected_resume_date": str(payload.expected_resume_date) if payload.expected_resume_date else None,
                    "active_candidates": impact["active_candidates"], "upcoming_interviews": interviews},
    )
    return get_requisition_detail_service(engine, requisition_id)


def resume_requisition_service(
    engine: Engine,
    requisition_id: int,
    payload: RequisitionResume,
    auth_context: AuthContext,
) -> RequisitionResponse:
    existing = find_requisition_by_id(engine, requisition_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Requisition was not found")
    if existing.status != "on-hold":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This requisition is not on hold")
    try:
        days = resume_from_hold(engine, requisition_id, user_id=auth_context.user.id, note=payload.note,
                                to_status=None, version=payload.version)
    except StaleWriteConflict as conflict:
        conflict.current = get_requisition_detail_service(engine, requisition_id)
        raise
    insert_audit_log(
        engine,
        actor_user_id=auth_context.user.id,
        location_id=auth_context.user.location_id,
        entity_type="requisition",
        entity_id=requisition_id,
        action_type="requisition.resume",
        old_values={"status": "on-hold"},
        new_values={"hold_days": days, "note": payload.note},
    )
    return get_requisition_detail_service(engine, requisition_id)


def list_requisition_holds_service(engine: Engine, requisition_id: int) -> list[RequisitionHoldResponse]:
    if not find_requisition_by_id(engine, requisition_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Requisition was not found")
    return [_hold_response(row) for row in list_holds(engine, requisition_id)]
