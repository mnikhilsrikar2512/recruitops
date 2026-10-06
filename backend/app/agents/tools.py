"""Read-only tool adapters for V1 agents.

Every tool reads through existing repositories and enforces scope: nothing
outside the caller's company (tenant_id), and non-company-wide callers only
what their office can already see.
Nothing here writes to domain tables — agents are draft-only.
"""
from __future__ import annotations

from fastapi import HTTPException, status

from app.repositories.candidates import (
    find_candidate_by_id,
    find_candidate_document_by_id,
    list_candidate_applications,
)
from app.repositories.daily_updates import list_daily_updates
from app.repositories.notifications import list_notifications
from app.repositories.requisitions import find_requisition_by_id
from app.repositories.workflow_actions import list_workflow_action_items
from app.schemas.daily_update import DailyUpdateListFilters
from app.schemas.notification import NotificationListFilters
from app.schemas.workflow_action import WorkflowActionQueueFilters
from app.services import scope


def _not_found(label: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{label} was not found")


def _iso(value) -> str | None:
    if value is None:
        return None
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


def _guard_location(record_location_id: int | None, scope_location_id: int | None, is_admin: bool) -> None:
    if is_admin or scope_location_id is None or record_location_id is None:
        return
    if record_location_id != scope_location_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Location scope does not allow this action",
        )


def read_candidate(
    *, engine, candidate_id: int, location_id: int | None, is_admin: bool, tenant_id: int | None = None
) -> dict:
    record = find_candidate_by_id(engine, candidate_id)
    if record is not None and not scope.candidate_in_tenant(engine, candidate_id, tenant_id):
        record = None  # another company's candidate is "not found"
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate was not found")

    applications = list_candidate_applications(engine, candidate_id)
    # Mirror the candidate service's own access rule: the actor's location
    # must intersect one of the candidate's application locations. The
    # previous "location_id in {None} | app_locations" branch let a
    # NULL-scope actor read anything, which is the opposite of safe.
    if not is_admin and location_id is not None and applications:
        app_locations = {app.location_id for app in applications}
        if app_locations and location_id not in app_locations:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Location scope does not allow this action",
            )

    return {
        "id": record.id,
        "full_name": record.full_name,
        "email": record.email,
        "phone": record.phone,
        "current_company": record.current_company,
        "current_designation": record.current_designation,
        "total_experience_years": record.total_experience_years,
        "notice_period_days": record.notice_period_days,
        "source_type": record.source_type,
        "source_detail": record.source_detail,
        "duplicate_state": record.duplicate_state,
        "profile_status": record.profile_status,
        "intake_stage": record.intake_stage,
        # getattr: record shapes vary between the real repository and test
        # stubs; resume fields are informational, never access control.
        "resume_file_name": getattr(record, "resume_file_name", None),
        "resume_file_path": getattr(record, "resume_file_path", None),
        "resume_uploaded_at": _iso(getattr(record, "resume_uploaded_at", None)),
    }


def read_candidate_resume(*, engine, candidate_id: int, candidate: dict | None = None) -> dict:
    # Reuse the already-loaded candidate instead of re-querying when given.
    if candidate is not None:
        return {
            "resume_file_name": candidate.get("resume_file_name"),
            "resume_file_path": candidate.get("resume_file_path"),
            "resume_uploaded_at": candidate.get("resume_uploaded_at"),
        }
    record = find_candidate_by_id(engine, candidate_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate was not found")
    return {
        "resume_file_name": record.resume_file_name,
        "resume_file_path": record.resume_file_path,
        "resume_uploaded_at": _iso(record.resume_uploaded_at),
    }


def read_candidate_document(
    *,
    engine,
    document_id: int,
    candidate_id: int,
    location_id: int | None,
    is_admin: bool,
    tenant_id: int | None = None,
) -> dict:
    """Validate that resume_document_id actually belongs to this candidate."""
    if not scope.candidate_in_tenant(engine, candidate_id, tenant_id):
        raise _not_found("Candidate document")
    try:
        document = find_candidate_document_by_id(engine, document_id)
    except RuntimeError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate document was not found",
        ) from None
    if document.candidate_id != candidate_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="resume_document_id does not belong to the given candidate",
        )
    _guard_location(getattr(document, "location_id", None), location_id, is_admin)
    return {
        "id": document.id,
        "document_type": document.document_type,
        "file_name": document.file_name,
        "file_path": document.file_path,
        "verification_status": document.verification_status,
    }


def read_requisition(
    *, engine, requisition_id: int, location_id: int | None, is_admin: bool, tenant_id: int | None = None
) -> dict:
    record = find_requisition_by_id(engine, requisition_id)
    if record is not None and tenant_id is not None and not scope.office_in_tenant(engine, record.location_id, tenant_id):
        record = None
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Requisition was not found")
    _guard_location(record.location_id, location_id, is_admin)
    return {
        "id": record.id,
        "title": record.title,
        "status": record.status,
        "priority": record.priority,
        "location_id": record.location_id,
        "client_name": record.client_name,
        "openings_count": record.openings_count,
        "work_mode": record.work_mode,
        "employment_type": record.employment_type,
        "job_description": record.job_description,
        "must_have_skills": record.must_have_skills,
        "good_to_have_skills": record.good_to_have_skills,
    }


def read_daily_updates(
    *, engine, scope: str, user_id: int, location_id: int | None, is_admin: bool, max_items: int,
    tenant_id: int | None = None,
) -> list[dict]:
    # Non-admins can only ever see their own updates or their location's;
    # "location" scope for a non-admin without a location silently narrows
    # to the user's own updates rather than leaking other branches' data.
    if scope == "me":
        filters = DailyUpdateListFilters(user_id=user_id, page=1, page_size=max_items)
    elif is_admin or location_id is not None:
        filters = DailyUpdateListFilters(location_id=location_id, page=1, page_size=max_items)
    else:
        filters = DailyUpdateListFilters(user_id=user_id, page=1, page_size=max_items)
    filters.tenant_id = tenant_id
    records, _total = list_daily_updates(engine, filters)
    return [
        {
            "id": record.id,
            "submitted_by_name": record.submitted_by_name,
            "requisition_title": record.requisition_title,
            "update_date": _iso(record.update_date),
            "summary": record.summary,
            "profiles_sourced_count": record.profiles_sourced_count,
            "profiles_screened_count": record.profiles_screened_count,
            "profiles_submitted_count": record.profiles_submitted_count,
            "interviews_scheduled_count": record.interviews_scheduled_count,
            "offers_closed_count": record.offers_closed_count,
            "blockers": record.blockers,
            "next_actions": record.next_actions,
        }
        for record in records
    ]


def read_workflow_queue(
    *,
    engine,
    actor_user_id: int,
    actor_location_id: int | None,
    actor_role_code: str,
    is_admin: bool,
    max_items: int,
    tenant_id: int | None = None,
) -> list[dict]:
    filters = WorkflowActionQueueFilters(status="open", page=1, page_size=max_items, tenant_id=tenant_id)
    records, _total = list_workflow_action_items(
        engine,
        actor_user_id=actor_user_id,
        actor_location_id=actor_location_id,
        actor_role_code=actor_role_code,
        is_admin=is_admin,
        filters=filters,
    )
    return [
        {
            "id": record.id,
            "action_key": record.action_key,
            "source": record.source,
            "title": record.title,
            "description": record.description,
            "priority": record.priority,
            "status": record.status,
            "entity_type": record.entity_type,
            "entity_id": record.entity_id,
            "age_label": record.age_label,
            "route_href": record.route_href,
            "due_at": _iso(record.due_at),
        }
        for record in records
    ]


def read_notifications(*, engine, user_id: int, status_name: str | None, max_items: int) -> list[dict]:
    filters = NotificationListFilters(status=status_name, page=1, page_size=max_items)
    records, _total = list_notifications(engine, user_id, filters)
    return [
        {
            "id": record.id,
            "module_name": record.module_name,
            "entity_type": record.entity_type,
            "entity_id": record.entity_id,
            "title": record.title,
            "message": record.message,
            "priority": record.priority,
            "status": record.status,
            "read_at": _iso(record.read_at),
            "created_at": _iso(record.created_at),
            "action_url": record.action_url,
        }
        for record in records
    ]
