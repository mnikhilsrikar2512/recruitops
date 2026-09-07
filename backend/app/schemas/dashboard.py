from pydantic import BaseModel


class RoleDashboardResponse(BaseModel):
    role_code: str
    location_id: int | None
    open_requisitions: int
    active_candidates: int
    active_applications: int
    pending_daily_updates: int


class MyWorkDashboardResponse(BaseModel):
    user_id: int
    owned_requisitions: int
    sourced_candidates: int
    active_pipeline_items: int
    submitted_updates: int


class LocationSummaryResponse(BaseModel):
    location_id: int
    location_name: str | None
    open_requisitions: int
    active_candidates: int
    active_applications: int
    submitted_profiles: int
    submitted_updates: int
    joined_applications: int


class CompanyLocationSummaryItem(BaseModel):
    location_id: int
    location_name: str | None
    open_requisitions: int
    active_candidates: int
    active_applications: int
    submitted_profiles: int
    submitted_updates: int
    joined_applications: int


class CompanySummaryResponse(BaseModel):
    total_locations: int
    total_open_requisitions: int
    total_active_candidates: int
    total_active_applications: int
    total_submitted_profiles: int
    total_submitted_updates: int
    total_joined_applications: int
    locations: list[CompanyLocationSummaryItem]
