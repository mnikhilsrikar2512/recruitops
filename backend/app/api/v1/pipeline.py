from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy import Engine

from app.api.deps import get_current_auth_context, get_engine, require_location_scope, require_permissions
from app.schemas.pipeline import (
    PipelineApplicationDetailResponse,
    PipelineBoardFilters,
    PipelineBoardItemResponse,
    PipelineHistoryItemResponse,
    PipelineStageMove,
    PipelineStageMoveResponse,
)
from app.services.pipeline import (
    get_pipeline_application_detail_service,
    get_pipeline_history_service,
    list_pipeline_board_service,
    move_pipeline_stage_service,
)
from app.services.auth import AuthContext

router = APIRouter(dependencies=[Depends(get_current_auth_context)])


@router.get("/board", response_model=list[PipelineBoardItemResponse])
def list_pipeline_board_endpoint(
    _auth: object = Depends(require_permissions("pipeline.read.summary")),
    _scope: object = Depends(require_location_scope("location_id")),
    auth_context: AuthContext = Depends(get_current_auth_context),
    requisition_id: int | None = Query(default=None, ge=1),
    owner_user_id: int | None = Query(default=None, ge=1),
    sourced_by_user_id: int | None = Query(default=None, ge=1),
    stage: str | None = Query(default=None),
    location_id: int | None = Query(default=None, ge=1),
    engine: Engine = Depends(get_engine),
) -> list[PipelineBoardItemResponse]:
    filters = PipelineBoardFilters(
        requisition_id=requisition_id,
        owner_user_id=owner_user_id,
        sourced_by_user_id=sourced_by_user_id,
        stage=stage,
        location_id=location_id,
    )
    return list_pipeline_board_service(engine, filters, auth_context)


@router.get("/applications/{application_id}", response_model=PipelineApplicationDetailResponse)
def get_pipeline_application_detail_endpoint(
    _auth: object = Depends(require_permissions("pipeline.read.detail")),
    auth_context: AuthContext = Depends(get_current_auth_context),
    application_id: int = Path(..., ge=1),
    engine: Engine = Depends(get_engine),
) -> PipelineApplicationDetailResponse:
    return get_pipeline_application_detail_service(engine, application_id, auth_context)


@router.patch("/applications/{application_id}/stage", response_model=PipelineStageMoveResponse)
def move_pipeline_stage_endpoint(
    payload: PipelineStageMove,
    _auth: object = Depends(require_permissions("pipeline.stage.move")),
    auth_context: AuthContext = Depends(get_current_auth_context),
    application_id: int = Path(..., ge=1),
    engine: Engine = Depends(get_engine),
) -> PipelineStageMoveResponse:
    return move_pipeline_stage_service(engine, application_id, payload, auth_context)


@router.get("/applications/{application_id}/history", response_model=list[PipelineHistoryItemResponse])
def get_pipeline_history_endpoint(
    _auth: object = Depends(require_permissions("pipeline.stage.history.read")),
    auth_context: AuthContext = Depends(get_current_auth_context),
    application_id: int = Path(..., ge=1),
    engine: Engine = Depends(get_engine),
) -> list[PipelineHistoryItemResponse]:
    return get_pipeline_history_service(engine, application_id, auth_context)
