from fastapi import HTTPException, UploadFile, status
from sqlalchemy import Engine

from app.repositories.candidates import (
    count_candidate_applications_for_requisition,
    count_active_candidate_applications,
    create_candidate,
    create_candidate_document,
    create_duplicate_review_case,
    finalize_candidate_into_requisition,
    find_candidate_by_id,
    find_duplicate_matches,
    list_candidate_applications,
    list_candidates,
    social_profiles_for_candidate,
    update_candidate,
    update_candidate_duplicate_state,
)
from app.repositories.audit import insert_audit_log
from app.repositories.requisitions import find_requisition_by_id
from app.repositories.users import find_user_by_id
from app.schemas.candidate import (
    CandidateCreate,
    CandidateDocumentCreate,
    CandidateDocumentResponse,
    CandidateDuplicateCheckResponse,
    CandidateDuplicateDecisionPayload,
    CandidateDuplicateReviewCaseResponse,
    CandidateFinalizePayload,
    CandidateFinalizeResponse,
    CandidateListFilters,
    CandidateListItemResponse,
    CandidateListResponse,
    CandidateOwnerReassignment,
    CandidateOwnerReassignmentResponse,
    CandidateResponse,
    CandidateUpdate,
)
from app.schemas.notification import NotificationCreate
from app.schemas.pagination import PaginationMeta
from app.core.storage import save_candidate_document
from app.services.auth import AuthContext
from app.services.notifications import create_notification_service


def _assert_user_exists(engine: Engine, user_id: int | None, label: str) -> None:
    if user_id is None:
        return
    user = find_user_by_id(engine, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{label} was not found")


def _can_access_candidate(candidate: CandidateResponse, auth_context: AuthContext) -> bool:
    if auth_context.user.role_code == "admin":
        return True

    actor_id = auth_context.user.id
    actor_location_id = auth_context.user.location_id
    direct_user_ids = {
        candidate.created_by_user_id,
        candidate.sourced_by_user_id,
        candidate.primary_owner_user_id,
    }
    if actor_id in direct_user_ids:
        return True

    for application in candidate.applications:
        if application.location_id == actor_location_id:
            return True
        if actor_id in {application.owner_user_id, application.submitted_by_user_id}:
            return True

    return False


def _assert_candidate_access(candidate: CandidateResponse, auth_context: AuthContext) -> None:
    if _can_access_candidate(candidate, auth_context):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Candidate access is not allowed")


def list_candidates_service(
    engine: Engine,
    filters: CandidateListFilters,
    auth_context: AuthContext | None = None,
) -> CandidateListResponse:
    if auth_context and auth_context.user.role_code != "admin" and filters.owner_user_id is None:
        filters = filters.model_copy(update={"owner_user_id": auth_context.user.id})
    items, total = list_candidates(engine, filters)
    response_items = [
        CandidateListItemResponse(
            id=item.id,
            candidate_code=item.candidate_code,
            branch_code=item.branch_code,
            full_name=item.full_name,
            email=item.email,
            phone=item.phone,
            current_company=item.current_company,
            current_designation=item.current_designation,
            source_type=item.source_type,
            source_detail=item.source_detail,
            duplicate_state=item.duplicate_state,
            sourced_by_user_id=item.sourced_by_user_id,
            sourced_by_name=item.sourced_by_name,
            primary_owner_user_id=item.primary_owner_user_id,
            primary_owner_name=item.primary_owner_name,
            profile_status=item.profile_status,
            intake_stage=item.intake_stage,
            applications_count=item.applications_count,
            linked_requisition_titles=item.linked_requisition_titles or [],
            updated_at=item.updated_at,
        )
        for item in items
    ]
    return CandidateListResponse(
        items=response_items,
        meta=PaginationMeta(page=filters.page, page_size=filters.page_size, total=total),
    )


def create_candidate_service(engine: Engine, payload: CandidateCreate) -> CandidateResponse:
    _assert_user_exists(engine, payload.primary_owner_user_id, "Primary owner user")
    _assert_user_exists(engine, payload.sourced_by_user_id, "Sourced by user")
    _assert_user_exists(engine, payload.created_by_user_id, "Created by user")
    created = create_candidate(engine, payload)
    if payload.primary_owner_user_id:
        try:
            create_notification_service(
                engine,
                NotificationCreate(
                    location_id=payload.created_by_location_id if hasattr(payload, 'created_by_location_id') else None,
                    user_id=payload.primary_owner_user_id,
                    event_type="candidate_assigned",
                    source_type="candidate",
                    source_id=created.id,
                    title="New candidate assigned to you",
                    message=(
                        f"{created.full_name} has been assigned to you as the sourcing owner. "
                        "Review the profile and start screening."
                    ),
                    priority="normal",
                    action_url=f"/candidates/{created.id}",
                ),
            )
        except Exception:
            pass
    return get_candidate_detail_service(engine, created.id)


def get_candidate_detail_service(
    engine: Engine,
    candidate_id: int,
    auth_context: AuthContext | None = None,
) -> CandidateResponse:
    candidate = find_candidate_by_id(engine, candidate_id)
    if not candidate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate was not found")
    applications = list_candidate_applications(engine, candidate_id)
    response = CandidateResponse(
        id=candidate.id,
        candidate_code=candidate.candidate_code,
        branch_code=candidate.branch_code,
        full_name=candidate.full_name,
        email=candidate.email,
        phone=candidate.phone,
        current_company=candidate.current_company,
        current_designation=candidate.current_designation,
        source_type=candidate.source_type,
        source_detail=candidate.source_detail,
        total_experience_years=candidate.total_experience_years,
        notice_period_days=candidate.notice_period_days,
        social_profiles=social_profiles_for_candidate(candidate),
        sourced_by_user_id=candidate.sourced_by_user_id,
        sourced_by_name=candidate.sourced_by_name,
        primary_owner_user_id=candidate.primary_owner_user_id,
        primary_owner_name=candidate.primary_owner_name,
        created_by_user_id=candidate.created_by_user_id,
        duplicate_state=candidate.duplicate_state,
        profile_status=candidate.profile_status,
        intake_stage=candidate.intake_stage,
        resume_file_name=candidate.resume_file_name,
        resume_file_path=candidate.resume_file_path,
        resume_uploaded_at=candidate.resume_uploaded_at,
        finalized_at=candidate.finalized_at,
        applications=applications,
        created_at=candidate.created_at,
        updated_at=candidate.updated_at,
    )
    if auth_context:
        _assert_candidate_access(response, auth_context)
    return response


def update_candidate_service(
    engine: Engine,
    candidate_id: int,
    payload: CandidateUpdate,
    auth_context: AuthContext | None = None,
) -> CandidateResponse:
    if auth_context:
        get_candidate_detail_service(engine, candidate_id, auth_context)
    else:
        existing = find_candidate_by_id(engine, candidate_id)
        if not existing:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate was not found")
    _assert_user_exists(engine, payload.primary_owner_user_id, "Primary owner user")
    _assert_user_exists(engine, payload.sourced_by_user_id, "Sourced by user")
    update_candidate(engine, candidate_id, payload)
    return get_candidate_detail_service(engine, candidate_id, auth_context)


def create_candidate_document_service(
    engine: Engine,
    candidate_id: int,
    payload: CandidateDocumentCreate,
    auth_context: AuthContext | None = None,
) -> CandidateDocumentResponse:
    if auth_context:
        get_candidate_detail_service(engine, candidate_id, auth_context)
    else:
        candidate = find_candidate_by_id(engine, candidate_id)
        if not candidate:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate was not found")
    if payload.uploaded_by_user_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="uploaded_by_user_id is required")
    _assert_user_exists(engine, payload.uploaded_by_user_id, "Uploaded by user")
    created = create_candidate_document(engine, candidate_id, payload)
    return CandidateDocumentResponse.model_validate(created)


async def upload_candidate_document_service(
    engine: Engine,
    candidate_id: int,
    file: UploadFile,
    document_type: str,
    auth_context: AuthContext | None = None,
) -> CandidateDocumentResponse:
    if auth_context:
        get_candidate_detail_service(engine, candidate_id, auth_context)
    else:
        candidate_record = find_candidate_by_id(engine, candidate_id)
        if not candidate_record:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate was not found")

    file_name, file_path = await save_candidate_document(candidate_id, file)
    uploaded_by_user_id = auth_context.user.id if auth_context else None
    payload = CandidateDocumentCreate(
        document_type=document_type,
        file_name=file_name,
        file_path=file_path,
        uploaded_by_user_id=uploaded_by_user_id,
    )
    created = create_candidate_document(engine, candidate_id, payload)
    return CandidateDocumentResponse.model_validate(created)


def get_candidate_duplicate_check_service(
    engine: Engine,
    candidate_id: int,
    auth_context: AuthContext | None = None,
) -> CandidateDuplicateCheckResponse:
    if auth_context:
        get_candidate_detail_service(engine, candidate_id, auth_context)
    else:
        candidate = find_candidate_by_id(engine, candidate_id)
        if not candidate:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate was not found")
    matches = find_duplicate_matches(engine, candidate_id)
    duplicate_state = "in-review" if matches else "cleared"
    update_candidate_duplicate_state(engine, candidate_id, duplicate_state)
    return CandidateDuplicateCheckResponse(candidate_id=candidate_id, duplicate_state=duplicate_state, matches=matches)


def create_candidate_duplicate_decision_service(
    engine: Engine,
    candidate_id: int,
    payload: CandidateDuplicateDecisionPayload,
    auth_context: AuthContext | None = None,
) -> CandidateDuplicateReviewCaseResponse:
    candidate = find_candidate_by_id(engine, candidate_id)
    if auth_context:
        get_candidate_detail_service(engine, candidate_id, auth_context)
    if not candidate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate was not found")
    if payload.requested_by_user_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="requested_by_user_id is required")
    _assert_user_exists(engine, payload.requested_by_user_id, "Requested by user")
    _assert_user_exists(engine, payload.assigned_reviewer_user_id, "Assigned reviewer user")
    if payload.matched_candidate_id:
        matched = find_candidate_by_id(engine, payload.matched_candidate_id)
        if not matched:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Matched candidate was not found")

    status_map = {
        "request_override": "override-requested",
        "link_existing": "approved",
        "discard_draft": "discarded",
    }
    candidate_state_map = {
        "request_override": "blocked",
        "link_existing": "merged",
        "discard_draft": "blocked",
    }
    update_candidate_duplicate_state(engine, candidate_id, candidate_state_map[payload.decision])
    case = create_duplicate_review_case(
        engine=engine,
        candidate_id=candidate_id,
        matched_candidate_id=payload.matched_candidate_id,
        decision_status=status_map[payload.decision],
        decision_notes=payload.decision_notes,
        requested_by_user_id=payload.requested_by_user_id,
        assigned_reviewer_user_id=payload.assigned_reviewer_user_id,
    )
    if payload.assigned_reviewer_user_id:
        try:
            create_notification_service(
                engine,
                NotificationCreate(
                    user_id=payload.assigned_reviewer_user_id,
                    event_type="duplicate_review_assigned",
                    source_type="candidate",
                    source_id=candidate_id,
                    title="Duplicate review to decide",
                    message=(
                        f"{candidate.full_name} may be a duplicate of an existing profile. "
                        "Open the review case to keep, link, or discard the draft."
                    ),
                    priority="high",
                    action_url=f"/candidates/{candidate_id}/duplicate-review",
                ),
            )
        except Exception:
            pass
    actor_user_id = payload.requested_by_user_id or (auth_context.user.id if auth_context else None)
    if actor_user_id is not None:
        insert_audit_log(
            engine,
            actor_user_id=actor_user_id,
            location_id=auth_context.user.location_id if auth_context else None,
            entity_type="candidate",
            entity_id=candidate_id,
            action_type="duplicate_decision_created",
            old_values={"duplicate_state": candidate.duplicate_state},
            new_values={
                "decision": payload.decision,
                "matched_candidate_id": payload.matched_candidate_id,
                "decision_status": case.decision_status,
            },
        )
    return CandidateDuplicateReviewCaseResponse.model_validate(case)


def finalize_candidate_service(
    engine: Engine,
    candidate_id: int,
    payload: CandidateFinalizePayload,
    auth_context: AuthContext | None = None,
) -> CandidateFinalizeResponse:
    if auth_context:
        candidate = get_candidate_detail_service(engine, candidate_id, auth_context)
    else:
        candidate = find_candidate_by_id(engine, candidate_id)
        if not candidate:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate was not found")
    if candidate.duplicate_state != "cleared":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Candidate duplicate check must be cleared before finalization",
        )
    requisition = find_requisition_by_id(engine, payload.requisition_id)
    if not requisition:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Requisition was not found")
    if count_candidate_applications_for_requisition(engine, candidate_id, payload.requisition_id) > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Candidate is already linked to this requisition",
        )
    owner = find_user_by_id(engine, payload.owner_user_id)
    if not owner:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application owner user was not found")
    if owner.primary_location_id != requisition.location_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Application owner user must belong to the requisition location",
        )
    _assert_user_exists(engine, payload.submitted_by_user_id, "Submitted by user")
    _assert_user_exists(engine, payload.finalized_by_user_id, "Finalized by user")
    finalized = finalize_candidate_into_requisition(engine, candidate_id, payload)
    if getattr(requisition, "primary_owner_user_id", None):
        try:
            create_notification_service(
                engine,
                NotificationCreate(
                    location_id=requisition.location_id,
                    user_id=requisition.primary_owner_user_id,
                    event_type="candidate_finalized",
                    source_type="requisition",
                    source_id=payload.requisition_id,
                    title="Candidate linked to a requisition",
                    message=(
                        f"{candidate.full_name} was finalized into {requisition.title}. "
                        "Open the requisition to confirm the move and plan next steps."
                    ),
                    priority="normal",
                    action_url=f"/requisitions/{payload.requisition_id}",
                ),
            )
        except Exception:
            pass
    return CandidateFinalizeResponse.model_validate(finalized)


def reassign_candidate_owner_service(
    engine: Engine,
    candidate_id: int,
    payload: CandidateOwnerReassignment,
    auth_context: AuthContext | None = None,
) -> CandidateOwnerReassignmentResponse:
    candidate = get_candidate_detail_service(engine, candidate_id, auth_context)
    _assert_user_exists(engine, payload.new_primary_owner_user_id, "Primary owner user")

    active_application_count = count_active_candidate_applications(engine, candidate_id)
    review_required = active_application_count > 0
    if review_required and not payload.review_confirmed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Owner reassignment requires active-work review confirmation",
        )

    update_candidate(
        engine,
        candidate_id,
        CandidateUpdate(primary_owner_user_id=payload.new_primary_owner_user_id),
    )
    try:
        create_notification_service(
            engine,
            NotificationCreate(
                location_id=candidate.applications[0].location_id if candidate.applications else None,
                user_id=payload.new_primary_owner_user_id,
                event_type="candidate_owner_reassigned",
                source_type="candidate",
                source_id=candidate_id,
                title="You now own a candidate",
                message=(
                    f"You are now the primary owner of {candidate.full_name}. "
                    "Open the profile and pick up their pipeline."
                ),
                priority="normal",
                action_url=f"/candidates/{candidate_id}",
            ),
        )
    except Exception:
        pass
    actor_user_id = payload.changed_by_user_id or (auth_context.user.id if auth_context else None)
    if actor_user_id is not None:
        insert_audit_log(
            engine,
            actor_user_id=actor_user_id,
            location_id=auth_context.user.location_id if auth_context else None,
            entity_type="candidate",
            entity_id=candidate_id,
            action_type="primary_owner_reassigned",
            old_values={"primary_owner_user_id": candidate.primary_owner_user_id},
            new_values={
                "primary_owner_user_id": payload.new_primary_owner_user_id,
                "reason": payload.reason,
                "review_confirmed": payload.review_confirmed,
                "active_application_count": active_application_count,
            },
        )
    return CandidateOwnerReassignmentResponse(
        candidate_id=candidate_id,
        previous_primary_owner_user_id=candidate.primary_owner_user_id,
        new_primary_owner_user_id=payload.new_primary_owner_user_id,
        active_application_count=active_application_count,
        review_required=review_required,
        reason=payload.reason,
    )
