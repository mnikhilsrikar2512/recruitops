from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy import Engine

from app.api.deps import get_current_auth_context, get_engine, require_location_scope, require_permissions
from app.schemas.interview import InterviewCreate, InterviewFeedbackUpdate, InterviewListFilters, InterviewListResponse, InterviewResponse
from app.services.auth import AuthContext
from app.services.interviews import create_interview_service, get_interview_detail_service, list_interviews_service, update_interview_feedback_service

router = APIRouter(dependencies=[Depends(get_current_auth_context)])


@router.get("/", response_model=InterviewListResponse)
def list_interviews_endpoint(
    _auth: object = Depends(require_permissions("interview.read")),
    _scope: object = Depends(require_location_scope("location_id")),
    auth_context: AuthContext = Depends(get_current_auth_context),
    candidate_application_id: int | None = Query(default=None, ge=1),
    location_id: int | None = Query(default=None, ge=1),
    interviewer_user_id: int | None = Query(default=None, ge=1),
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    engine: Engine = Depends(get_engine),
) -> InterviewListResponse:
    filters = InterviewListFilters(
        candidate_application_id=candidate_application_id,
        location_id=location_id,
        interviewer_user_id=interviewer_user_id,
        status=status,
        page=page,
        page_size=page_size,
    )
    return list_interviews_service(engine, filters, auth_context)


@router.post("/", response_model=InterviewResponse, status_code=201)
def create_interview_endpoint(
    payload: InterviewCreate,
    _auth: object = Depends(require_permissions("interview.create")),
    auth_context: AuthContext = Depends(get_current_auth_context),
    engine: Engine = Depends(get_engine),
) -> InterviewResponse:
    return create_interview_service(engine, payload, auth_context)


@router.get("/{interview_id}", response_model=InterviewResponse)
def get_interview_detail_endpoint(
    _auth: object = Depends(require_permissions("interview.read")),
    auth_context: AuthContext = Depends(get_current_auth_context),
    interview_id: int = Path(..., ge=1),
    engine: Engine = Depends(get_engine),
) -> InterviewResponse:
    return get_interview_detail_service(engine, interview_id, auth_context)


@router.patch("/{interview_id}/feedback", response_model=InterviewResponse)
def submit_interview_feedback_endpoint(
    payload: InterviewFeedbackUpdate,
    _auth: object = Depends(require_permissions("interview.feedback.submit")),
    auth_context: AuthContext = Depends(get_current_auth_context),
    interview_id: int = Path(..., ge=1),
    engine: Engine = Depends(get_engine),
) -> InterviewResponse:
    return update_interview_feedback_service(engine, interview_id, payload, auth_context)
