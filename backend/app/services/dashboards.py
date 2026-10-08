from fastapi import HTTPException, status
from sqlalchemy import Engine

from app.repositories.dashboards import (
    get_location_summary_counts,
    get_my_work_dashboard_counts,
    get_role_dashboard_counts,
    list_company_location_summaries,
)
from app.schemas.dashboard import (
    CompanyLocationSummaryItem,
    CompanySummaryResponse,
    LocationSummaryResponse,
    MyWorkDashboardResponse,
    RoleDashboardResponse,
)
from app.services import scope
from app.services.auth import AuthContext


def get_role_dashboard_service(engine: Engine, auth_context: AuthContext) -> RoleDashboardResponse:
    counts = get_role_dashboard_counts(
        engine,
        actor_user_id=auth_context.user.id,
        actor_location_id=auth_context.user.location_id,
        is_admin=scope.is_company_wide(auth_context),
        tenant_id=scope.tenant_id_of(auth_context),
    )
    return RoleDashboardResponse(
        role_code=auth_context.user.role_code,
        location_id=auth_context.user.location_id,
        open_requisitions=counts.open_requisitions,
        active_candidates=counts.active_candidates,
        active_applications=counts.active_applications,
        pending_daily_updates=counts.pending_daily_updates,
    )


def get_my_work_dashboard_service(engine: Engine, auth_context: AuthContext) -> MyWorkDashboardResponse:
    counts = get_my_work_dashboard_counts(engine, auth_context.user.id)
    return MyWorkDashboardResponse(
        user_id=auth_context.user.id,
        owned_requisitions=counts.owned_requisitions,
        sourced_candidates=counts.sourced_candidates,
        active_pipeline_items=counts.active_pipeline_items,
        submitted_updates=counts.submitted_updates,
    )


def get_location_summary_service(
    engine: Engine,
    auth_context: AuthContext,
    location_id: int | None,
) -> LocationSummaryResponse:
    resolved_location_id = location_id
    if scope.is_company_wide(auth_context):
        if resolved_location_id is not None and not scope.can_reach_office(engine, auth_context, resolved_location_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location summary was not found")
    else:
        if auth_context.user.location_id is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Location summary is not allowed")
        if resolved_location_id is None:
            resolved_location_id = auth_context.user.location_id
        elif resolved_location_id != auth_context.user.location_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Location summary is not allowed")

    if resolved_location_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="location_id is required")

    try:
        counts = get_location_summary_counts(engine, resolved_location_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location summary was not found") from exc
    return LocationSummaryResponse(
        location_id=counts.location_id,
        location_name=counts.location_name,
        open_requisitions=counts.open_requisitions,
        active_candidates=counts.active_candidates,
        active_applications=counts.active_applications,
        submitted_profiles=counts.submitted_profiles,
        submitted_updates=counts.submitted_updates,
        joined_applications=counts.joined_applications,
    )


def get_company_summary_service(engine: Engine, auth_context: AuthContext) -> CompanySummaryResponse:
    if not scope.is_company_wide(auth_context):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Company summary is not allowed")

    items = list_company_location_summaries(engine, scope.tenant_id_of(auth_context))
    return CompanySummaryResponse(
        total_locations=len(items),
        total_open_requisitions=sum(item.open_requisitions for item in items),
        total_active_candidates=sum(item.active_candidates for item in items),
        total_active_applications=sum(item.active_applications for item in items),
        total_submitted_profiles=sum(item.submitted_profiles for item in items),
        total_submitted_updates=sum(item.submitted_updates for item in items),
        total_joined_applications=sum(item.joined_applications for item in items),
        locations=[
            CompanyLocationSummaryItem(
                location_id=item.location_id,
                location_name=item.location_name,
                open_requisitions=item.open_requisitions,
                active_candidates=item.active_candidates,
                active_applications=item.active_applications,
                submitted_profiles=item.submitted_profiles,
                submitted_updates=item.submitted_updates,
                joined_applications=item.joined_applications,
            )
            for item in items
        ],
    )
