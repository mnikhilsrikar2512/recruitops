from fastapi import HTTPException, status
from sqlalchemy import Engine

from app.repositories.interviews import create_interview, find_interview_by_id, list_interviews, update_interview_feedback
from app.repositories.pipeline import find_pipeline_application_by_id
from app.repositories.users import find_user_by_id
from app.schemas.interview import (
    InterviewCreate,
    InterviewFeedbackUpdate,
    InterviewListFilters,
    InterviewListResponse,
    InterviewResponse,
)
from app.schemas.pagination import PaginationMeta
from app.services.auth import AuthContext
from app.services.pipeline import _assert_pipeline_application_access


def list_interviews_service(
    engine: Engine,
    filters: InterviewListFilters,
    auth_context: AuthContext | None = None,
) -> InterviewListResponse:
    if auth_context and auth_context.user.role_code != "admin" and filters.location_id is None:
        filters = filters.model_copy(update={"location_id": auth_context.user.location_id})
    items, total = list_interviews(engine, filters)
    return InterviewListResponse(
        items=[InterviewResponse.model_validate(item) for item in items],
        meta=PaginationMeta(page=filters.page, page_size=filters.page_size, total=total),
    )


def get_interview_detail_service(
    engine: Engine,
    interview_id: int,
    auth_context: AuthContext | None = None,
) -> InterviewResponse:
    interview = find_interview_by_id(engine, interview_id)
    if not interview:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview was not found")
    application = find_pipeline_application_by_id(engine, interview.candidate_application_id)
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pipeline application was not found")
    if auth_context:
        _assert_pipeline_application_access(application, auth_context)
    return InterviewResponse.model_validate(interview)


def create_interview_service(
    engine: Engine,
    payload: InterviewCreate,
    auth_context: AuthContext | None = None,
) -> InterviewResponse:
    application = find_pipeline_application_by_id(engine, payload.candidate_application_id)
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pipeline application was not found")
    if auth_context:
        _assert_pipeline_application_access(application, auth_context)
    if payload.interviewer_user_id and not find_user_by_id(engine, payload.interviewer_user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interviewer user was not found")
    created_by_user_id = payload.created_by_user_id
    if created_by_user_id is None and auth_context:
        created_by_user_id = auth_context.user.id
    if created_by_user_id is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Created by user is required")
    created = create_interview(engine, payload.model_copy(update={"created_by_user_id": created_by_user_id}))
    return InterviewResponse.model_validate(created)


def update_interview_feedback_service(
    engine: Engine,
    interview_id: int,
    payload: InterviewFeedbackUpdate,
    auth_context: AuthContext | None = None,
) -> InterviewResponse:
    get_interview_detail_service(engine, interview_id, auth_context)
    updated = update_interview_feedback(engine, interview_id, payload)
    return InterviewResponse.model_validate(updated)
