from fastapi import HTTPException, status
from sqlalchemy import Engine

from app.core.stage_buckets import BUCKET_LABELS, BUCKET_ORDER, TERMINAL_BUCKETS
from app.repositories.audit import insert_audit_log
from app.repositories.display_ids import find_branch_by_id
from app.repositories.pipeline import (
    application_has_pipeline_template,
    find_pipeline_application_by_id,
    find_pipeline_template_stage_for_application,
    list_pipeline_board,
    list_pipeline_history,
    move_pipeline_stage,
    reopen_application,
    resolve_application_stage_bucket,
)
from app.repositories.users import find_user_by_id
from app.schemas.pipeline import (
    PipelineApplicationDetailResponse,
    PipelineBoardFilters,
    PipelineBoardItemResponse,
    PipelineHistoryItemResponse,
    PipelineReopen,
    PipelineStageMove,
    PipelineStageMoveResponse,
)
from app.schemas.notification import NotificationCreate
from app.services import scope
from app.services.auth import AuthContext
from app.services.notifications import create_notification_service


def _stage_bucket(engine: Engine, application_id: int, stage: str, definition: object | None) -> str:
    """Bucket of a stage for this application: the template stage's own
    bucket when it has one, else the database resolver (company map ->
    platform map -> name)."""
    bucket = getattr(definition, "metric_bucket", None) if definition is not None else None
    return bucket or resolve_application_stage_bucket(engine, application_id, stage)


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

    # Phase 4.6: rules read metric buckets, never raw labels, so a company's
    # own stage names ("Onboarding", "Candidate Pulled Out") get the same
    # guards as the baseline ones.
    current_bucket = _stage_bucket(engine, application_id, application.current_stage, current_stage_definition)
    target_bucket = _stage_bucket(engine, application_id, payload.to_stage, target_stage_definition)
    notes = getattr(payload, "notes", None)
    reason = notes or payload.rejection_reason

    is_closed = application.application_status in TERMINAL_BUCKETS or current_bucket in TERMINAL_BUCKETS
    if is_closed and payload.to_stage != application.current_stage:
        closed_as = application.application_status if application.application_status in TERMINAL_BUCKETS else current_bucket
        if closed_as == "joined":
            detail = "Joined applications cannot move to another stage; reopen the application first"
        else:
            detail = f"This application is closed ({BUCKET_LABELS.get(closed_as, closed_as)}); reopen it before moving it"
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)

    # Closing moves (reject, withdraw, join) are never "backward".
    is_backward = False
    if target_bucket not in TERMINAL_BUCKETS:
        if current_stage_definition and target_stage_definition:
            is_backward = target_stage_definition.stage_order < current_stage_definition.stage_order
        else:
            is_backward = BUCKET_ORDER.get(target_bucket, 0) < BUCKET_ORDER.get(current_bucket, 0)
    if is_backward and not notes:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Backward stage movement needs a reason; add a note explaining why the candidate moves back",
        )

    is_target_rejection = target_bucket == "rejected" or (
        target_stage_definition is not None and target_stage_definition.stage_type == "rejection"
    )
    is_target_withdrawal = target_bucket == "withdrawn"
    is_target_joining = target_bucket == "joined" or (
        target_stage_definition is not None and target_stage_definition.stage_type == "joining"
    )

    if is_target_rejection and not payload.rejection_reason:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Rejection reason is required for rejection stages",
        )

    if is_target_withdrawal and not reason:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="A reason is required when a candidate withdraws",
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
    if target_bucket == "offer" and not is_target_rejection and not is_target_joining:
        branch = find_branch_by_id(engine, application.location_id)
        if branch is not None and branch.offers_enabled is False:
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


def reopen_pipeline_application_service(
    engine: Engine,
    application_id: int,
    payload: PipelineReopen,
    auth_context: AuthContext,
) -> PipelineStageMoveResponse:
    """Phase 4.6: bring a Rejected / Withdrawn / Joined application back into
    an open stage. Needs pipeline.stage.reopen and a reason; history stays
    append-only (a new 'reopen' row), and the action is audited."""
    application = get_pipeline_application_detail_service(engine, application_id, auth_context)
    current_bucket = resolve_application_stage_bucket(engine, application_id, application.current_stage)
    if application.application_status not in TERMINAL_BUCKETS and current_bucket not in TERMINAL_BUCKETS:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only rejected, withdrawn or joined applications can be reopened",
        )
    target_definition = find_pipeline_template_stage_for_application(engine, application_id, payload.to_stage)
    if application_has_pipeline_template(engine, application_id) and target_definition is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Target stage does not belong to the active pipeline template",
        )
    target_bucket = _stage_bucket(engine, application_id, payload.to_stage, target_definition)
    if target_bucket in TERMINAL_BUCKETS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Reopen into an open stage (not Rejected, Withdrawn or Joined)",
        )
    from_stage, updated = reopen_application(engine, application_id, payload.to_stage, payload.reason, auth_context.user.id)
    insert_audit_log(
        engine,
        actor_user_id=auth_context.user.id,
        location_id=updated.location_id,
        entity_type="candidate_application",
        entity_id=application_id,
        action_type="pipeline.reopen",
        old_values={"stage": from_stage, "application_status": application.application_status},
        new_values={"stage": updated.current_stage, "application_status": updated.application_status, "reason": payload.reason},
    )
    return PipelineStageMoveResponse(
        application_id=application_id,
        from_stage=from_stage,
        to_stage=updated.current_stage,
        application_status=updated.application_status,
        stage_updated_at=updated.stage_updated_at,
    )
