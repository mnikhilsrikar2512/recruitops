from fastapi import APIRouter, Depends, File, Path, Query, UploadFile
from sqlalchemy import Engine

from app.api.deps import get_current_auth_context, get_engine, require_any_permission, require_permissions
from app.schemas.candidate import (
    CandidateCreate,
    CandidateFootprintResponse,
    CandidateDocumentCreate,
    CandidateDocumentResponse,
    CandidateDuplicateCheckResponse,
    CandidateDuplicateDecisionPayload,
    CandidateDuplicateReviewCaseResponse,
    CandidateFinalizePayload,
    CandidateFinalizeResponse,
    CandidateListFilters,
    CandidateListResponse,
    CandidateOwnerReassignment,
    CandidateOwnerReassignmentResponse,
    CandidateResponse,
    CandidateUpdate,
)
from app.services.candidates import (
    create_candidate_document_service,
    create_candidate_duplicate_decision_service,
    create_candidate_service,
    finalize_candidate_service,
    get_candidate_detail_service,
    get_candidate_duplicate_check_service,
    get_candidate_footprint_service,
    list_candidates_service,
    reassign_candidate_owner_service,
    update_candidate_service,
    upload_candidate_document_service,
)
from app.services.auth import AuthContext

router = APIRouter()


@router.get("/", response_model=CandidateListResponse)
def list_candidates_endpoint(
    auth_context: AuthContext = Depends(require_permissions("candidate.read")),
    search: str | None = Query(default=None),
    requisition_id: int | None = Query(default=None, ge=1),
    source_type: str | None = Query(default=None),
    duplicate_state: str | None = Query(default=None),
    owner_user_id: int | None = Query(default=None, ge=1),
    sourced_by_user_id: int | None = Query(default=None, ge=1),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    engine: Engine = Depends(get_engine),
) -> CandidateListResponse:
    filters = CandidateListFilters(
        search=search,
        requisition_id=requisition_id,
        source_type=source_type,
        duplicate_state=duplicate_state,
        owner_user_id=owner_user_id,
        sourced_by_user_id=sourced_by_user_id,
        page=page,
        page_size=page_size,
    )
    return list_candidates_service(engine, filters, auth_context)


@router.post("/", response_model=CandidateResponse, status_code=201)
def create_candidate_endpoint(
    payload: CandidateCreate,
    auth_context: AuthContext = Depends(require_permissions("candidate.create")),
    engine: Engine = Depends(get_engine),
) -> CandidateResponse:
    return create_candidate_service(engine, payload)


@router.get("/{candidate_id}", response_model=CandidateResponse)
def get_candidate_detail_endpoint(
    auth_context: AuthContext = Depends(require_permissions("candidate.read")),
    candidate_id: int = Path(..., ge=1),
    engine: Engine = Depends(get_engine),
) -> CandidateResponse:
    return get_candidate_detail_service(engine, candidate_id, auth_context)


@router.get("/{candidate_id}/footprint", response_model=CandidateFootprintResponse)
def get_candidate_footprint_endpoint(
    auth_context: AuthContext = Depends(get_current_auth_context),
    candidate_id: int = Path(..., ge=1),
    engine: Engine = Depends(get_engine),
) -> CandidateFootprintResponse:
    """Admin-only: cross-tenant client footprint for one shared candidate.

    Gated on the admin role inside the service (this oversight view crosses
    tenant lines by design, so it must not be grantable via permissions);
    requires a valid session for the audit trail either way.
    """
    return get_candidate_footprint_service(engine, candidate_id, auth_context)


@router.patch("/{candidate_id}", response_model=CandidateResponse)
def update_candidate_endpoint(
    payload: CandidateUpdate,
    auth_context: AuthContext = Depends(require_permissions("candidate.update")),
    candidate_id: int = Path(..., ge=1),
    engine: Engine = Depends(get_engine),
) -> CandidateResponse:
    return update_candidate_service(engine, candidate_id, payload, auth_context)


@router.post("/{candidate_id}/documents", response_model=CandidateDocumentResponse, status_code=201)
def create_candidate_document_endpoint(
    payload: CandidateDocumentCreate,
    auth_context: AuthContext = Depends(require_permissions("candidate.resume.upload")),
    candidate_id: int = Path(..., ge=1),
    engine: Engine = Depends(get_engine),
) -> CandidateDocumentResponse:
    return create_candidate_document_service(engine, candidate_id, payload, auth_context)


@router.post("/{candidate_id}/upload", response_model=CandidateDocumentResponse, status_code=201)
async def upload_candidate_document_endpoint(
    file: UploadFile = File(...),
    document_type: str = Query(default="other"),
    auth_context: AuthContext = Depends(require_permissions("candidate.resume.upload")),
    candidate_id: int = Path(..., ge=1),
    engine: Engine = Depends(get_engine),
) -> CandidateDocumentResponse:
    return await upload_candidate_document_service(engine, candidate_id, file, document_type, auth_context)


@router.get("/{candidate_id}/duplicate-check", response_model=CandidateDuplicateCheckResponse)
def get_candidate_duplicate_check_endpoint(
    auth_context: AuthContext = Depends(require_permissions("candidate.duplicate.check")),
    candidate_id: int = Path(..., ge=1),
    engine: Engine = Depends(get_engine),
) -> CandidateDuplicateCheckResponse:
    return get_candidate_duplicate_check_service(engine, candidate_id, auth_context)


@router.post("/{candidate_id}/duplicate-check/decision", response_model=CandidateDuplicateReviewCaseResponse, status_code=201)
def create_candidate_duplicate_decision_endpoint(
    payload: CandidateDuplicateDecisionPayload,
    auth_context: AuthContext = Depends(
        require_any_permission(
            "candidate.duplicate.request_override",
            "candidate.duplicate.link_existing",
            "candidate.duplicate.discard_draft",
        )
    ),
    candidate_id: int = Path(..., ge=1),
    engine: Engine = Depends(get_engine),
) -> CandidateDuplicateReviewCaseResponse:
    return create_candidate_duplicate_decision_service(engine, candidate_id, payload, auth_context)


@router.post("/{candidate_id}/finalize-profile", response_model=CandidateFinalizeResponse, status_code=201)
def finalize_candidate_endpoint(
    payload: CandidateFinalizePayload,
    auth_context: AuthContext = Depends(require_permissions("candidate.link_requisition")),
    candidate_id: int = Path(..., ge=1),
    engine: Engine = Depends(get_engine),
) -> CandidateFinalizeResponse:
    return finalize_candidate_service(engine, candidate_id, payload, auth_context)


@router.post("/{candidate_id}/applications", response_model=CandidateFinalizeResponse, status_code=201)
def create_candidate_application_endpoint(
    payload: CandidateFinalizePayload,
    auth_context: AuthContext = Depends(require_permissions("candidate.link_requisition")),
    candidate_id: int = Path(..., ge=1),
    engine: Engine = Depends(get_engine),
) -> CandidateFinalizeResponse:
    return finalize_candidate_service(engine, candidate_id, payload, auth_context)


@router.post("/{candidate_id}/reassign-owner", response_model=CandidateOwnerReassignmentResponse)
def reassign_candidate_owner_endpoint(
    payload: CandidateOwnerReassignment,
    auth_context: AuthContext = Depends(require_permissions("candidate.update")),
    candidate_id: int = Path(..., ge=1),
    engine: Engine = Depends(get_engine),
) -> CandidateOwnerReassignmentResponse:
    return reassign_candidate_owner_service(engine, candidate_id, payload, auth_context)
