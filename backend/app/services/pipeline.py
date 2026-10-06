from fastapi import HTTPException, status
from sqlalchemy import Engine

from app.repositories.display_ids import find_branch_by_id
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
from app.services import scope
from app.services.auth import AuthContext
from app.services.notifications import create_notification_service


def _can_access_pipeline_application(
    application: PipelineApplicationDetailResponse,
    auth_context: AuthContext,
    engine: Engine | None = None,
) -> bool:
    # Company boundary first: an application on another company's office is
    # never reachable, whatever role or contribution the caller has.
    if engine is not None and not scope.office_in_tenant(
        engine, application.location_id, scope.tenant_id_of(auth_context)
    ):
        return False
    if scope.is_company_wide(auth_context):
        return True

    actor_id = auth_context.user.id
    actor_location_id = auth_context.user.location_id
    # Tenant (location) scope first: the application belongs to exactly one
    # requisition/branch, so users outside that tenant only get in via a
    # contribution role ON THIS application (never via a contribution made
    # for a different tenant, e.g. the global candidate's original source).
    if application.location_id == actor_location_id:
        return True
    if actor_id in {application.owner_user_id, application.submitted_by_user_id}:
        return True
    # NOTE: sourced_by_user_id is intentionally NOT a grant here — it is
    # projected from the GLOBAL candidate record (c.created_by_user_id) onto
    # every application, so treating it as access would let the original
    # source recruiter read other tenants' applications, notes, and offer
    # terms for a candidate they once sourced. Tenant isolation wins.
    return False


def _assert_pipeline_application_access(
    application: PipelineApplicationDetailResponse,
    auth_context: AuthContext,
    engine: Engine | None = None,
) -> None:
    if engine is not None and not scope.office_in_tenant(
        engine, application.location_id, scope.tenant_id_of(auth_context)
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pipeline application was not found")
    if _can_access_pipeline_application(application, auth_context, engine):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Pipeline access is not allowed")


def list_pipeline_board_service(
    engine: Engine,
    filters: PipelineBoardFilters,
    auth_context: AuthContext | None = None,
) -> list[PipelineBoardItemResponse]:
    if auth_context and not scope.is_company_wide(auth_context) and filters.location_id is None:
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
        _assert_pipeline_application_access(response, auth_context, engine)
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

    # Offer-phase streamlining: branches with offer tracking disabled treat
    # the offer stage as out of scope — candidates are handed off to the
    # client instead. Joins/starts remain reachable (they close the loop
    # without a tracked offer), as does rejection.
    if not is_target_rejection and not is_target_joining:
        branch = find_branch_by_id(engine, application.location_id)
        if branch is not None and branch.offers_enabled is False and (
            (payload.to_stage or "").strip().lower() in {"offer", "offers"}
            or "offer" in str(payload.to_stage or "").strip().lower()
            or (target_stage_definition is not None and "offer" in str(target_stage_definition.stage_code or "").strip().lower())
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Offer stage is not tracked for this branch; hand off the candidate to the client instead",
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
