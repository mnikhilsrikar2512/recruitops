from fastapi import HTTPException, status
from sqlalchemy import Engine

from app.repositories.pipeline import (
    application_has_pipeline_template,
    find_pipeline_application_by_id,
    find_pipeline_template_stage_for_application,
    list_pipeline_board,
    list_pipeline_history,
    move_pipeline_stage,
)
from app.repositories.users import find_user_by_id
from app.schemas.pipeline import (
    PipelineApplicationDetailResponse,
    PipelineBoardFilters,
    PipelineBoardItemResponse,
    PipelineHistoryItemResponse,
    PipelineStageMove,
    PipelineStageMoveResponse,
)
from app.schemas.notification import NotificationCreate
from app.services.auth import AuthContext
from app.services.notifications import create_notification_service


def _can_access_pipeline_application(
    application: PipelineApplicationDetailResponse,
    auth_context: AuthContext,
) -> bool:
    if auth_context.user.role_code == "admin":
        return True

    actor_id = auth_context.user.id
    actor_location_id = auth_context.user.location_id
    if application.location_id == actor_location_id:
        return True
    if actor_id in {
        application.owner_user_id,
        application.submitted_by_user_id,
        application.sourced_by_user_id,
    }:
        return True
    return False


def _assert_pipeline_application_access(
    application: PipelineApplicationDetailResponse,
    auth_context: AuthContext,
) -> None:
    if _can_access_pipeline_application(application, auth_context):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Pipeline access is not allowed")


def list_pipeline_board_service(
    engine: Engine,
    filters: PipelineBoardFilters,
    auth_context: AuthContext | None = None,
) -> list[PipelineBoardItemResponse]:
    if auth_context and auth_context.user.role_code != "admin" and filters.location_id is None:
        filters = filters.model_copy(update={"location_id": auth_context.user.location_id})
    items = list_pipeline_board(engine, filters)
    return [PipelineBoardItemResponse.model_validate(item) for item in items]


def get_pipeline_application_detail_service(
    engine: Engine,
    application_id: int,
    auth_context: AuthContext | None = None,
) -> PipelineApplicationDetailResponse:
    application = find_pipeline_application_by_id(engine, application_id)
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pipeline application was not found")
    response = PipelineApplicationDetailResponse.model_validate(application)
    if auth_context:
        _assert_pipeline_application_access(response, auth_context)
    return response


def move_pipeline_stage_service(
    engine: Engine,
    application_id: int,
    payload: PipelineStageMove,
    auth_context: AuthContext | None = None,
) -> PipelineStageMoveResponse:
    if auth_context:
        application = get_pipeline_application_detail_service(engine, application_id, auth_context)
    else:
        application = find_pipeline_application_by_id(engine, application_id)
        if not application:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pipeline application was not found")
    if payload.changed_by_user_id:
        user = find_user_by_id(engine, payload.changed_by_user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Changed by user was not found")

    current_stage_definition = find_pipeline_template_stage_for_application(
        engine,
        application_id,
        application.current_stage,
    )
    target_stage_definition = find_pipeline_template_stage_for_application(
        engine,
        application_id,
        payload.to_stage,
    )
    if application_has_pipeline_template(engine, application_id) and target_stage_definition is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Target stage does not belong to the active pipeline template",
        )

    if current_stage_definition and target_stage_definition:
        if target_stage_definition.stage_order < current_stage_definition.stage_order:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Backward stage movement is not allowed without an exception flow",
            )

    is_joined_state = application.application_status == "joined" or application.current_stage in {"joined", "hired"}
    is_target_rejection = (
        (target_stage_definition is not None and target_stage_definition.stage_type == "rejection")
        or payload.to_stage in {"rejected", "client-rejected"}
    )
    is_target_joining = (
        (target_stage_definition is not None and target_stage_definition.stage_type == "joining")
        or payload.to_stage in {"joined", "hired"}
    )

    if is_joined_state and payload.to_stage != application.current_stage:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Joined applications cannot move to another stage without a restore workflow",
        )

    if is_target_rejection and not payload.rejection_reason:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Rejection reason is required for rejection stages",
        )

    if (
        is_target_rejection
        and current_stage_definition is not None
        and not current_stage_definition.allows_rejection
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Rejection is not allowed from the current stage",
        )

    if is_target_joining and payload.joining_date is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Joining date is required for joining stages",
        )

    from_stage, updated = move_pipeline_stage(engine, application_id, payload)

    if updated.owner_user_id:
        try:
            create_notification_service(
                engine,
                NotificationCreate(
                    location_id=updated.location_id,
                    user_id=updated.owner_user_id,
                    event_type="pipeline_stage_changed",
                    source_type="pipeline",
                    source_id=application_id,
                    title="Stage moved in the pipeline",
                    message=(
                        f"{application.candidate_name} moved from {from_stage} to "
                        f"{payload.to_stage} on {application.requisition_title}. "
                        "Open the pipeline board to continue their review."
                    ),
                    priority="normal",
                    action_url=f"/pipeline/applications/{application_id}",
                ),
            )
        except Exception:
            pass

    return PipelineStageMoveResponse(
        application_id=application_id,
        from_stage=from_stage,
        to_stage=updated.current_stage,
        application_status=updated.application_status,
        stage_updated_at=updated.stage_updated_at,
    )


def get_pipeline_history_service(
    engine: Engine,
    application_id: int,
    auth_context: AuthContext | None = None,
) -> list[PipelineHistoryItemResponse]:
    if auth_context:
        get_pipeline_application_detail_service(engine, application_id, auth_context)
    else:
        application = find_pipeline_application_by_id(engine, application_id)
        if not application:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pipeline application was not found")
    items = list_pipeline_history(engine, application_id)
    return [PipelineHistoryItemResponse.model_validate(item) for item in items]
