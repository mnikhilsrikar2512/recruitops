from fastapi import APIRouter, Depends, Query
from sqlalchemy import Engine

from app.api.deps import get_current_auth_context, get_engine, require_permissions
from app.schemas.dashboard import (
    CompanySummaryResponse,
    LocationSummaryResponse,
    MyWorkDashboardResponse,
    RoleDashboardResponse,
)
from app.services.auth import AuthContext
from app.services.dashboards import (
    get_company_summary_service,
    get_location_summary_service,
    get_my_work_dashboard_service,
    get_role_dashboard_service,
)

router = APIRouter()


@router.get("/role", response_model=RoleDashboardResponse)
def role_dashboard_endpoint(
    _auth: object = Depends(require_permissions("dashboard.read_pipeline_summary")),
    auth_context: AuthContext = Depends(get_current_auth_context),
    engine: Engine = Depends(get_engine),
) -> RoleDashboardResponse:
    return get_role_dashboard_service(engine, auth_context)


@router.get("/my-work", response_model=MyWorkDashboardResponse)
def my_work_dashboard_endpoint(
    _auth: object = Depends(require_permissions("dashboard.read_my_work")),
    auth_context: AuthContext = Depends(get_current_auth_context),
    engine: Engine = Depends(get_engine),
) -> MyWorkDashboardResponse:
    return get_my_work_dashboard_service(engine, auth_context)


@router.get("/location-summary", response_model=LocationSummaryResponse)
def location_summary_endpoint(
    _auth: object = Depends(require_permissions("dashboard.read_pipeline_summary")),
    auth_context: AuthContext = Depends(get_current_auth_context),
    location_id: int | None = Query(default=None, ge=1),
    engine: Engine = Depends(get_engine),
) -> LocationSummaryResponse:
    return get_location_summary_service(engine, auth_context, location_id)


@router.get("/company-summary", response_model=CompanySummaryResponse)
def company_summary_endpoint(
    _auth: object = Depends(require_permissions("dashboard.read_pipeline_summary")),
    auth_context: AuthContext = Depends(get_current_auth_context),
    engine: Engine = Depends(get_engine),
) -> CompanySummaryResponse:
    return get_company_summary_service(engine, auth_context)
