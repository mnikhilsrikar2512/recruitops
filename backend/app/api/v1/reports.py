"""Reports API — time-to-fill, source effectiveness, placements, client summary,
and report datasets."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import Engine

from app.api.deps import get_current_auth_context, get_engine, require_permissions
from app.schemas.reports import (
    ClientSummaryReportResponse,
    PlacementsReportResponse,
    ReportDatasetResponse,
    SourceEffectivenessReportResponse,
    TimeToFillReportResponse,
    WithdrawalReasonsReportResponse,
)
from app.services.auth import AuthContext
from app.services.reports import (
    get_client_summary_report_service,
    get_placements_report_service,
    get_report_dataset_service,
    get_report_datasets_service,
    get_source_effectiveness_report_service,
    get_time_to_fill_report_service,
    get_withdrawal_reasons_report_service,
)

router = APIRouter()


@router.get("/time-to-fill", response_model=TimeToFillReportResponse)
def time_to_fill_endpoint(
    _auth: object = Depends(require_permissions("report.read")),
    auth_context: AuthContext = Depends(get_current_auth_context),
    engine: Engine = Depends(get_engine),
) -> TimeToFillReportResponse:
    return get_time_to_fill_report_service(engine, auth_context)


@router.get("/source-effectiveness", response_model=SourceEffectivenessReportResponse)
def source_effectiveness_endpoint(
    _auth: object = Depends(require_permissions("report.read")),
    auth_context: AuthContext = Depends(get_current_auth_context),
    engine: Engine = Depends(get_engine),
) -> SourceEffectivenessReportResponse:
    return get_source_effectiveness_report_service(engine, auth_context)


@router.get("/withdrawal-reasons", response_model=WithdrawalReasonsReportResponse)
def withdrawal_reasons_endpoint(
    _auth: object = Depends(require_permissions("report.read")),
    auth_context: AuthContext = Depends(get_current_auth_context),
    engine: Engine = Depends(get_engine),
) -> WithdrawalReasonsReportResponse:
    """Phase 4.11: why candidates withdrew, incl. after an offer."""
    return get_withdrawal_reasons_report_service(engine, auth_context)


@router.get("/placements", response_model=PlacementsReportResponse)
def placements_report_endpoint(
    _auth: object = Depends(require_permissions("report.read")),
    auth_context: AuthContext = Depends(get_current_auth_context),
    engine: Engine = Depends(get_engine),
    period_from: str | None = Query(default=None),
    period_to: str | None = Query(default=None),
) -> PlacementsReportResponse:
    return get_placements_report_service(engine, auth_context, period_from, period_to)


@router.get("/client-summary", response_model=ClientSummaryReportResponse)
def client_summary_report_endpoint(
    _auth: object = Depends(require_permissions("report.read")),
    auth_context: AuthContext = Depends(get_current_auth_context),
    engine: Engine = Depends(get_engine),
    period_from: str | None = Query(default=None),
    period_to: str | None = Query(default=None),
) -> ClientSummaryReportResponse:
    return get_client_summary_report_service(engine, auth_context, period_from, period_to)


@router.get("/datasets", response_model=ReportDatasetResponse)
def report_datasets_endpoint(
    _auth: object = Depends(require_permissions("report.read")),
    auth_context: AuthContext = Depends(get_current_auth_context),
    engine: Engine = Depends(get_engine),
) -> ReportDatasetResponse:
    return get_report_datasets_service(engine)


@router.get("/datasets/{dataset}", response_model=ReportDatasetResponse)
def report_dataset_endpoint(
    dataset: str,
    _auth: object = Depends(require_permissions("report.read")),
    auth_context: AuthContext = Depends(get_current_auth_context),
    engine: Engine = Depends(get_engine),
) -> ReportDatasetResponse:
    return get_report_dataset_service(engine, auth_context, dataset)
