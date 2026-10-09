"""Privacy requests (Phase 5.3, PRD §9.7). Company admins only
(privacy_request.write); every request is limited to the caller's company."""
from fastapi import APIRouter, BackgroundTasks, Depends, Path
from sqlalchemy import Engine

from app.api.deps import get_engine, require_permissions
from app.schemas.privacy import (
    CandidateEraseRequest,
    CompanyDeleteRequest,
    DownloadLink,
    PrivacyRequestResponse,
    SelfConfirmRequest,
)
from app.services import privacy

router = APIRouter()
WRITE = "privacy_request.write"


@router.get("/requests", response_model=list[PrivacyRequestResponse])
def list_privacy_requests_endpoint(auth=Depends(require_permissions(WRITE)), engine: Engine = Depends(get_engine)):
    return privacy.list_service(engine, auth)


@router.get("/requests/{request_id}", response_model=PrivacyRequestResponse)
def get_privacy_request_endpoint(request_id: int = Path(..., ge=1), auth=Depends(require_permissions(WRITE)),
                                 engine: Engine = Depends(get_engine)):
    return privacy.detail_service(engine, auth, request_id)


@router.post("/export-request", response_model=PrivacyRequestResponse, status_code=202)
def company_export_endpoint(background: BackgroundTasks, auth=Depends(require_permissions(WRITE)),
                            engine: Engine = Depends(get_engine)):
    """Every record of the company (incl. AI run logs) as a zip, built in the background."""
    return privacy.company_export_service(engine, auth, background)


@router.post("/delete-request", response_model=PrivacyRequestResponse, status_code=202)
def company_delete_endpoint(payload: CompanyDeleteRequest, auth=Depends(require_permissions(WRITE)),
                            engine: Engine = Depends(get_engine)):
    """Needs a second admin's approval (or the sole admin's two-step code), then 7 days to cancel."""
    return privacy.company_delete_service(engine, auth, payload.reason)


@router.post("/requests/{request_id}/confirm", response_model=PrivacyRequestResponse)
def self_confirm_endpoint(payload: SelfConfirmRequest, request_id: int = Path(..., ge=1),
                          auth=Depends(require_permissions(WRITE)), engine: Engine = Depends(get_engine)):
    return privacy.self_confirm_service(engine, auth, request_id, payload.code)


@router.post("/requests/{request_id}/cancel", response_model=PrivacyRequestResponse)
def cancel_endpoint(request_id: int = Path(..., ge=1), auth=Depends(require_permissions(WRITE)),
                    engine: Engine = Depends(get_engine)):
    return privacy.cancel_service(engine, auth, request_id)


@router.post("/requests/{request_id}/download", response_model=DownloadLink)
def download_endpoint(request_id: int = Path(..., ge=1), auth=Depends(require_permissions(WRITE)),
                      engine: Engine = Depends(get_engine)):
    """A short-lived link to the export zip (audited)."""
    return privacy.download_service(engine, auth, request_id)


@router.post("/candidates/{candidate_id}/export", response_model=PrivacyRequestResponse, status_code=201)
def candidate_export_endpoint(candidate_id: int = Path(..., ge=1), auth=Depends(require_permissions(WRITE)),
                              engine: Engine = Depends(get_engine)):
    return privacy.candidate_export_service(engine, auth, candidate_id)


@router.post("/candidates/{candidate_id}/erase", response_model=PrivacyRequestResponse)
def candidate_erase_endpoint(payload: CandidateEraseRequest, candidate_id: int = Path(..., ge=1),
                             auth=Depends(require_permissions(WRITE)), engine: Engine = Depends(get_engine)):
    return privacy.candidate_erase_service(engine, auth, candidate_id, payload.confirm, payload.reason)
