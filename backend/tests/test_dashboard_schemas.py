from app.schemas.dashboard import (
    CompanyLocationSummaryItem,
    CompanySummaryResponse,
    LocationSummaryResponse,
    MyWorkDashboardResponse,
    RoleDashboardResponse,
)


def test_role_dashboard_response_shape() -> None:
    payload = RoleDashboardResponse(
        role_code="recruiter",
        location_id=1,
        open_requisitions=2,
        active_candidates=4,
        active_applications=3,
        pending_daily_updates=1,
    )
    assert payload.role_code == "recruiter"
    assert payload.open_requisitions == 2


def test_my_work_dashboard_response_shape() -> None:
    payload = MyWorkDashboardResponse(
        user_id=5,
        owned_requisitions=2,
        sourced_candidates=7,
        active_pipeline_items=4,
        submitted_updates=3,
    )
    assert payload.user_id == 5
    assert payload.submitted_updates == 3


def test_location_summary_response_shape() -> None:
    payload = LocationSummaryResponse(
        location_id=1,
        location_name="Hyderabad",
        open_requisitions=2,
        active_candidates=5,
        active_applications=4,
        submitted_profiles=3,
        submitted_updates=6,
        joined_applications=1,
    )
    assert payload.location_id == 1
    assert payload.joined_applications == 1


def test_company_summary_response_shape() -> None:
    payload = CompanySummaryResponse(
        total_locations=1,
        total_open_requisitions=2,
        total_active_candidates=5,
        total_active_applications=4,
        total_submitted_profiles=3,
        total_submitted_updates=6,
        total_joined_applications=1,
        locations=[
            CompanyLocationSummaryItem(
                location_id=1,
                location_name="Hyderabad",
                open_requisitions=2,
                active_candidates=5,
                active_applications=4,
                submitted_profiles=3,
                submitted_updates=6,
                joined_applications=1,
            )
        ],
    )
    assert payload.total_locations == 1
    assert payload.locations[0].location_name == "Hyderabad"
