from fastapi import HTTPException, UploadFile, status
from sqlalchemy import Engine
from app.repositories.versioning import StaleWriteConflict

from app.repositories.candidates import (
    find_candidate_document_by_id,
    archive_candidate,
    count_open_applications_in_tenant,
    find_open_candidate_archive,
    restore_candidate,
    count_candidate_applications_for_requisition,
    count_active_candidate_applications,
    create_candidate,
    create_candidate_document,
    create_duplicate_review_case,
    finalize_candidate_into_requisition,
    find_candidate_by_id,
    find_duplicate_matches,
    get_candidate_footprint,
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
    FileLinkResponse,
    CandidateFootprintEntry,
    CandidateFootprintResponse,
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
from app.core.config import settings
from app.core.file_storage import get_storage
from app.repositories.uploads import find_idempotent_document, remember_idempotent_document
from app.services.uploads import ingest, read_capped
from app.services import scope
from app.services.auth import AuthContext
from app.services.notifications import create_notification_service
from app.services.cross_tenant_signals import check_and_record_cross_tenant_signal


def _assert_user_exists(engine: Engine, user_id: int | None, label: str) -> None:
    if user_id is None:
        return
    user = find_user_by_id(engine, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{label} was not found")


def _can_access_candidate(candidate: CandidateResponse, auth_context: AuthContext) -> bool:
    # Company boundary is enforced first in get_candidate_detail_service.
    if scope.is_company_wide(auth_context):
        return True

    actor_id = auth_context.user.id
    actor_location_id = auth_context.user.location_id
    # Global-record ownership (creator/sourcer/primary owner) grants visibility
    # of the candidate IDENTITY only — application summaries are filtered to
    # the viewer's tenant below, so grants never cross tenant lines.
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


def _tenant_scoped_candidate_response(
    candidate: CandidateResponse, auth_context: AuthContext
) -> CandidateResponse:
    """Filter application summaries to the viewer's tenant.

    Candidates are global identity records, but pipeline state, requisition
    links, and owner details per application are tenant-owned. A user whose
    only tie is a global-record grant (e.g. they sourced the candidate for
    tenant A) must not see tenant B's application summaries.
    """
    if scope.is_company_wide(auth_context):
        return candidate
    actor_id = auth_context.user.id
    actor_location_id = auth_context.user.location_id
    global_record_grant_only = actor_id in {
        candidate.created_by_user_id,
        candidate.sourced_by_user_id,
        candidate.primary_owner_user_id,
    } and not any(
        application.location_id == actor_location_id
        or actor_id in {application.owner_user_id, application.submitted_by_user_id}
        for application in candidate.applications
    )
    if global_record_grant_only:
        return candidate.model_copy(update={"applications": []})
    scoped = [
        application
        for application in candidate.applications
        if application.location_id == actor_location_id
        or actor_id in {application.owner_user_id, application.submitted_by_user_id}
    ]
    if len(scoped) != len(candidate.applications):
        return candidate.model_copy(update={"applications": scoped})
    return candidate


def _assert_candidate_access(candidate: CandidateResponse, auth_context: AuthContext) -> None:
    if _can_access_candidate(candidate, auth_context):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Candidate access is not allowed")


def get_candidate_footprint_service(
    engine: Engine,
    candidate_id: int,
    auth_context: AuthContext | None = None,
) -> CandidateFootprintResponse:
    """Admin-only cross-tenant oversight: which clients a shared candidate is
    in play with. Recruiters must use tenant-scoped surfaces instead — the
    footprint's value is precisely that it crosses tenant lines, so it is
    gated on the admin ROLE (not a permission that can be granted) and never
    carries tenant-private fields."""
    if auth_context is None or not scope.is_company_wide(auth_context):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Candidate footprint is restricted to administrator oversight",
        )
    candidate = find_candidate_by_id(engine, candidate_id)
    if not candidate or not scope.candidate_in_tenant(engine, candidate_id, scope.tenant_id_of(auth_context)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate was not found")
    # D-04: the footprint never crosses company lines.
    offices = scope.company_office_ids(engine, auth_context)
    entries = [
        entry for entry in get_candidate_footprint(engine, candidate_id)
        if offices is None or entry.branch_id in offices
    ]
    return CandidateFootprintResponse(
        candidate_id=candidate.id,
        candidate_code=candidate.candidate_code,
        full_name=candidate.full_name,
        entries=[CandidateFootprintEntry.model_validate(entry) for entry in entries],
        clients_count=len({entry.client_id for entry in entries if entry.client_id is not None}),
    )


def list_candidates_service(
    engine: Engine,
    filters: CandidateListFilters,
    auth_context: AuthContext | None = None,
) -> CandidateListResponse:
    if auth_context and not scope.is_company_wide(auth_context) and filters.owner_user_id is None:
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
    include_archived: bool = False,
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
        version=getattr(candidate, "version", 1) or 1,
    )
    if auth_context:
        # Another company's candidate is indistinguishable from a missing one.
        if not scope.candidate_in_tenant(engine, candidate_id, scope.tenant_id_of(auth_context)):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate was not found")
        _assert_candidate_access(response, auth_context)
        response = _tenant_scoped_candidate_response(response, auth_context)
        # Phase 4.4: archived for this company -> gone, unless the caller
        # may archive/restore (then it is shown, marked archived).
        archive = find_open_candidate_archive(engine, candidate_id, scope.tenant_id_of(auth_context))
        if archive is not None:
            if not include_archived:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate was not found")
            response = response.model_copy(
                update={"archived_at": archive.archived_at, "archive_reason": archive.archive_reason}
            )
        offices = scope.company_office_ids(engine, auth_context)
        if offices is not None:
            own = [a for a in response.applications if a.location_id in offices]
            if len(own) != len(response.applications):
                response = response.model_copy(update={"applications": own})
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
    try:
        update_candidate(engine, candidate_id, payload)
    except StaleWriteConflict as conflict:
        conflict.current = get_candidate_detail_service(engine, candidate_id, auth_context)
        raise
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
    idempotency_key: str | None = None,
) -> CandidateDocumentResponse:
    """Phase 4.1/4.2: sniff + allowlist + size cap + quarantine + malware scan,
    then store under the company's prefix. A retried upload carrying the same
    Idempotency-Key returns the first result instead of a second copy."""
    if auth_context:
        get_candidate_detail_service(engine, candidate_id, auth_context)
    else:
        candidate_record = find_candidate_by_id(engine, candidate_id)
        if not candidate_record:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate was not found")

    uploaded_by_user_id = auth_context.user.id if auth_context else None
    key = (idempotency_key or "").strip()[:100] or None
    if key and uploaded_by_user_id is not None:
        previous = find_idempotent_document(engine, uploaded_by_user_id, key, "candidate", candidate_id)
        if previous is not None:
            return CandidateDocumentResponse.model_validate(find_candidate_document_by_id(engine, int(previous)))

    purpose = "resume" if document_type == "resume" else "document"
    content = await read_capped(file, purpose)
    stored = ingest(
        engine,
        content=content,
        file_name=file.filename or "",
        purpose=purpose,
        tenant_id=scope.tenant_id_of(auth_context) if auth_context else None,
        area="candidates",
        entity_type="candidate",
        entity_id=candidate_id,
        actor_user_id=uploaded_by_user_id,
        actor_location_id=auth_context.user.location_id if auth_context else None,
    )
    payload = CandidateDocumentCreate(
        document_type=document_type,
        file_name=stored.file_name,
        file_path=stored.storage_key,
        uploaded_by_user_id=uploaded_by_user_id,
    )
    created = create_candidate_document(engine, candidate_id, payload, stored)
    if key and uploaded_by_user_id is not None:
        remember_idempotent_document(engine, uploaded_by_user_id, key, "candidate", candidate_id, int(created.id))
    return CandidateDocumentResponse.model_validate(created)


def candidate_document_link_service(
    engine: Engine, candidate_id: int, document_id: int, auth_context: AuthContext
) -> FileLinkResponse:
    """Phase 4.1: a link is issued only after the caller passed the same
    access checks as reading the candidate, only for a clean scanned file,
    and only for a short time."""
    get_candidate_detail_service(engine, candidate_id, auth_context)
    try:
        document = find_candidate_document_by_id(engine, document_id)
    except RuntimeError:
        document = None
    if document is None or int(document.candidate_id) != int(candidate_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document was not found")
    if not document.storage_key or document.scan_status != "clean":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This document has no checked file to download")
    ttl = settings.file_link_ttl_seconds
    url = get_storage().link(document.storage_key, document.file_name, document.content_type or "application/octet-stream", ttl)
    return FileLinkResponse(url=url, expires_in_seconds=ttl, file_name=document.file_name,
                            content_type=document.content_type or "application/octet-stream")


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
    matches = find_duplicate_matches(
        engine, candidate_id, scope.tenant_id_of(auth_context) if auth_context else None
    )
    # Phase 4.7: only exact (e-mail/phone) matches flag the candidate;
    # similar-name suggestions are hints and never block.
    duplicate_state = "in-review" if any(m.match_tier == "exact" for m in matches) else "cleared"
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
    if getattr(requisition, "status", None) == "on-hold":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This requisition is on hold; new candidates can be added when it resumes",
        )
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
    response = CandidateFinalizeResponse.model_validate(finalized)
    # 030: lightweight cross-company duplicate-submission flag. Never
    # blocks or fails the finalize — a problem here is a missed flag,
    # not a broken finalize.
    try:
        response.cross_tenant_flag = check_and_record_cross_tenant_signal(
            engine,
            tenant_id=scope.tenant_id_of(auth_context) if auth_context else None,
            candidate_id=candidate_id,
            requisition_id=payload.requisition_id,
            application_id=finalized.application_id,
            email=getattr(candidate, "email", None),
            phone=getattr(candidate, "phone", None),
            client_name=getattr(requisition, "client_name", None),
        )
    except Exception:
        pass
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
    return response


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


def _require_company(auth_context: AuthContext) -> int:
    tenant_id = scope.tenant_id_of(auth_context)
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Archiving belongs to a company; sign in as a company user")
    return int(tenant_id)


def archive_candidate_service(engine: Engine, candidate_id: int, reason: str, auth_context: AuthContext) -> CandidateResponse:
    """Phase 4.4 (D-07): hide a candidate from this company. Nothing is
    deleted; other companies working the same person are not affected."""
    tenant_id = _require_company(auth_context)
    get_candidate_detail_service(engine, candidate_id, auth_context, include_archived=True)
    if find_open_candidate_archive(engine, candidate_id, tenant_id) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Candidate is already archived")
    open_applications = count_open_applications_in_tenant(engine, candidate_id, tenant_id)
    if open_applications:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Candidate has {open_applications} open application(s); close or withdraw them before archiving",
        )
    archive_candidate(engine, candidate_id, tenant_id, auth_context.user.id, reason)
    insert_audit_log(
        engine,
        actor_user_id=auth_context.user.id,
        location_id=auth_context.user.location_id,
        entity_type="candidate",
        entity_id=candidate_id,
        action_type="candidate.archive",
        new_values={"tenant_id": tenant_id, "reason": reason},
    )
    return get_candidate_detail_service(engine, candidate_id, auth_context, include_archived=True)


def restore_candidate_service(engine: Engine, candidate_id: int, auth_context: AuthContext) -> CandidateResponse:
    tenant_id = _require_company(auth_context)
    archive = find_open_candidate_archive(engine, candidate_id, tenant_id)
    if archive is None:
        get_candidate_detail_service(engine, candidate_id, auth_context, include_archived=True)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Candidate is not archived")
    get_candidate_detail_service(engine, candidate_id, auth_context, include_archived=True)
    restore_candidate(engine, archive.id, candidate_id, auth_context.user.id)
    insert_audit_log(
        engine,
        actor_user_id=auth_context.user.id,
        location_id=auth_context.user.location_id,
        entity_type="candidate",
        entity_id=candidate_id,
        action_type="candidate.restore",
        old_values={"archived_at": archive.archived_at, "reason": archive.archive_reason},
    )
    return get_candidate_detail_service(engine, candidate_id, auth_context)
