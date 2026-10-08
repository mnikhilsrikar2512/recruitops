"""Client stage lists (Phase 4.10, D-4.10): per client only."""
from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import Engine

from app.repositories.audit import insert_audit_log
from app.repositories.clients import find_client_by_id
from app.repositories.stage_lists import (
    StageDef,
    StageList,
    StageRemapRequired,
    get_stage_list,
    list_client_stage_lists,
    save_stage_list,
    stage_options_for_application,
)
from app.schemas.stage_lists import (
    ClientStageListSummary,
    StageListOverview,
    StageListResponse,
    StageListUpdate,
    StageResponse,
)
from app.services import scope
from app.services.auth import AuthContext


def _tenant(auth_context: AuthContext) -> int:
    tenant_id = scope.tenant_id_of(auth_context)
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Stage lists belong to a company; sign in as a company user")
    return int(tenant_id)


def _client_in_company(engine: Engine, auth_context: AuthContext, client_id: int):
    client = find_client_by_id(engine, client_id)
    if client is None or not scope.office_in_tenant(engine, client.location_id, scope.tenant_id_of(auth_context)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client was not found")
    return client


def _response(stage_list: StageList, client_name: str | None = None) -> StageListResponse:
    return StageListResponse(
        template_id=stage_list.template_id,
        source=stage_list.source,
        client_company_id=stage_list.client_company_id,
        client_name=client_name,
        stages=[StageResponse(**stage) for stage in stage_list.stages],
    )


def get_overview_service(engine: Engine, auth_context: AuthContext) -> StageListOverview:
    tenant_id = _tenant(auth_context)
    return StageListOverview(
        company=_response(get_stage_list(engine, tenant_id, None)),
        clients=[ClientStageListSummary(**row) for row in list_client_stage_lists(engine, tenant_id)],
    )


def get_client_list_service(engine: Engine, auth_context: AuthContext, client_id: int) -> StageListResponse:
    client = _client_in_company(engine, auth_context, client_id)
    return _response(get_stage_list(engine, _tenant(auth_context), client_id), client.client_name)


def save_list_service(
    engine: Engine,
    auth_context: AuthContext,
    payload: StageListUpdate,
    client_id: int | None,
) -> StageListResponse:
    tenant_id = _tenant(auth_context)
    client = _client_in_company(engine, auth_context, client_id) if client_id is not None else None
    before = get_stage_list(engine, tenant_id, client_id)
    if not any(stage.bucket not in ("joined", "rejected", "withdrawn") for stage in payload.stages):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Add at least one working stage (not only closing stages)")
    try:
        template_id = save_stage_list(
            engine,
            tenant_id=tenant_id,
            client_company_id=client_id,
            stages=[StageDef(stage.name, stage.bucket, stage.allows_rejection) for stage in payload.stages],
            remap=payload.remap,
            user_id=auth_context.user.id,
            location_id=client.location_id if client else auth_context.user.location_id,
        )
    except StageRemapRequired as needed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "Some candidates are in stages this list removes. Choose where each of those stages goes.",
                "unmapped": needed.unmapped,
                "allowed_targets": needed.allowed,
            },
        ) from None
    after = get_stage_list(engine, tenant_id, client_id)
    insert_audit_log(
        engine,
        actor_user_id=auth_context.user.id,
        location_id=auth_context.user.location_id,
        entity_type="pipeline_template",
        entity_id=template_id,
        action_type="stage_list.saved",
        old_values={"source": before.source, "stages": [s["name"] for s in before.stages]},
        new_values={"client_id": client_id, "stages": [s["name"] for s in after.stages], "remap": payload.remap},
    )
    return _response(after, client.client_name if client else None)


def application_stage_options_service(engine: Engine, application_id: int) -> StageListResponse:
    return _response(stage_options_for_application(engine, application_id))
