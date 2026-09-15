"""Reports services — orchestration between repository and schemas."""
from __future__ import annotations

from datetime import date, timedelta

from fastapi import HTTPException, status
from sqlalchemy import Engine

from app.repositories.reports import (
    get_client_summary,
    get_dominant_currency,
    get_report_dataset,
    get_source_effectiveness,
    get_time_to_fill_breakdown,
    get_time_to_fill_summary,
    get_placements,
)
from app.schemas.reports import (
    ClientSummaryReportResponse,
    ClientSummaryRow,
    ClientSummaryTotals,
    PlacementRow,
    PlacementsReportResponse,
    PlacementsSummary,
    ReportColumn,
    ReportDatasetResponse,
    ReportDimension,
    SourceEffectivenessReportResponse,
    SourceEffectivenessRow,
    TimeToFillBreakdown,
    TimeToFillReportResponse,
    TimeToFillSummary,
)
from app.services.auth import AuthContext


def _resolve_period(from_str: str | None, to_str: str | None) -> tuple[date, date]:
    """Defaults to the current calendar month; validates ordering loudly."""
    today = date.today()
    try:
        period_from = date.fromisoformat(from_str) if from_str else today.replace(day=1)
        period_to = (
            date.fromisoformat(to_str)
            if to_str
            else (today.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Period must use ISO dates (YYYY-MM-DD)",
        ) from exc
    if period_to < period_from:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="period_to must be on or after period_from",
        )
    return period_from, period_to


def get_time_to_fill_report_service(engine: Engine, auth_context: AuthContext) -> TimeToFillReportResponse:
    is_admin = auth_context.user.role_code == "admin"
    location_id = auth_context.user.location_id
    summary = get_time_to_fill_summary(engine, location_id, is_admin)
    by_department = get_time_to_fill_breakdown(engine, "department", location_id, is_admin)
    by_seniority = get_time_to_fill_breakdown(engine, "seniority", location_id, is_admin)

    within_sla_percent = (
        round((summary.within_sla / summary.filled_count) * 100, 1)
        if summary.filled_count
        else None
    )
    return TimeToFillReportResponse(
        summary=TimeToFillSummary(
            filled_count=summary.filled_count,
            avg_days=summary.avg_days,
            fastest_days=summary.fastest_days,
            fastest_requisition=summary.fastest_requisition,
            slowest_days=summary.slowest_days,
            slowest_requisition=summary.slowest_requisition,
            within_sla=summary.within_sla,
            within_sla_percent=within_sla_percent,
        ),
        by_department=[TimeToFillBreakdown(**row.__dict__) for row in by_department],
        by_seniority=[TimeToFillBreakdown(**row.__dict__) for row in by_seniority],
    )


def get_source_effectiveness_report_service(
    engine: Engine, auth_context: AuthContext
) -> SourceEffectivenessReportResponse:
    is_admin = auth_context.user.role_code == "admin"
    rows = get_source_effectiveness(engine, auth_context.user.location_id, is_admin)

    total_candidates = sum(row.candidates for row in rows)
    converted = [
        SourceEffectivenessRow(
            source=row.source,
            candidates=row.candidates,
            hired=row.hired,
            conversion_rate=round((row.hired / row.candidates) * 100, 1) if row.candidates else None,
            # Quality score: hires weighted against volume, scaled to 0-10.
            quality_score=round(min(10.0, (row.hired / max(total_candidates, 1)) * 100 * 2), 1)
            if row.hired
            else None,
        )
        for row in rows
    ]
    best = max(
        (row for row in converted if row.conversion_rate is not None),
        key=lambda row: row.conversion_rate or 0,
        default=None,
    )
    return SourceEffectivenessReportResponse(
        total_sources=len(rows),
        best_source=best.source if best else None,
        best_source_conversion=best.conversion_rate if best else None,
        rows=converted,
    )


REPORT_DIMENSIONS = [
    ReportDimension(
        key="time_to_fill",
        label="Time to Fill",
        columns=[
            ReportColumn(key="title", label="Requisition", type="string"),
            ReportColumn(key="department", label="Department", type="string"),
            ReportColumn(key="days_to_fill", label="Days to Fill", type="number"),
            ReportColumn(key="sla_days", label="SLA Target (days)", type="number"),
            ReportColumn(key="sla_status", label="SLA Status", type="string"),
        ],
    ),
    ReportDimension(
        key="source_effectiveness",
        label="Source Effectiveness",
        columns=[
            ReportColumn(key="source", label="Source", type="string"),
            ReportColumn(key="candidates", label="Candidates", type="number"),
            ReportColumn(key="hired", label="Hired", type="number"),
        ],
    ),
    ReportDimension(
        key="pipeline",
        label="Active Pipeline",
        columns=[
            ReportColumn(key="requisition", label="Requisition", type="string"),
            ReportColumn(key="candidate", label="Candidate", type="string"),
            ReportColumn(key="stage", label="Stage", type="string"),
            ReportColumn(key="stage_updated_at", label="Stage Updated", type="date"),
        ],
    ),
    ReportDimension(
        key="requisitions",
        label="Requisitions",
        columns=[
            ReportColumn(key="title", label="Title", type="string"),
            ReportColumn(key="department", label="Department", type="string"),
            ReportColumn(key="status", label="Status", type="string"),
            ReportColumn(key="priority", label="Priority", type="string"),
            ReportColumn(key="open_positions", label="Open Positions", type="number"),
            ReportColumn(key="target_close_date", label="Target Close", type="date"),
        ],
    ),
    ReportDimension(
        key="sla",
        label="SLA Tracker",
        columns=[
            ReportColumn(key="mandate", label="Mandate", type="string"),
            ReportColumn(key="client", label="Client", type="string"),
            ReportColumn(key="sla_target_days", label="SLA Target (days)", type="number"),
            ReportColumn(key="current_days", label="Current Days", type="number"),
            ReportColumn(key="status", label="Status", type="string"),
            ReportColumn(key="owner", label="Owner", type="string"),
        ],
    ),
    ReportDimension(
        key="daily_updates",
        label="Daily Updates",
        columns=[
            ReportColumn(key="update_date", label="Date", type="date"),
            ReportColumn(key="submitted_by", label="Submitted By", type="string"),
            ReportColumn(key="requisition", label="Requisition", type="string"),
            ReportColumn(key="summary", label="Summary", type="string"),
            ReportColumn(key="blockers", label="Blockers", type="string"),
        ],
    ),
]


def get_report_datasets_service(engine: Engine) -> ReportDatasetResponse:
    del engine
    return ReportDatasetResponse(dimensions=REPORT_DIMENSIONS)


def get_report_dataset_service(
    engine: Engine, auth_context: AuthContext, dataset: str
) -> ReportDatasetResponse:
    """Run the named dataset query and return its rows plus its column schema."""
    dimension = next((d for d in REPORT_DIMENSIONS if d.key == dataset), None)
    if dimension is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown report dataset: {dataset}",
        )
    is_admin = auth_context.user.role_code == "admin"
    record = get_report_dataset(engine, dataset, auth_context.user.location_id, is_admin)
    return ReportDatasetResponse(dimensions=[dimension], rows=record.rows)


def get_placements_report_service(
    engine: Engine,
    auth_context: AuthContext,
    period_from: str | None,
    period_to: str | None,
) -> PlacementsReportResponse:
    start, end = _resolve_period(period_from, period_to)
    is_admin = auth_context.user.role_code == "admin"
    records = get_placements(
        engine, start, end, auth_context.user.location_id, is_admin
    )
    total_ctc = sum(r.ctc or 0 for r in records) or None
    total_revenue = round(sum(r.revenue for r in records), 2)
    filled = [
        (r.days_to_fill, r.joining_date)
        for r in records
        if r.days_to_fill is not None and r.joining_date is not None
    ]
    avg_days = round(sum(d for d, _ in filled) / len(filled), 1) if filled else None
    currency = next((r.currency for r in records if r.currency), None) or get_dominant_currency(
        engine
    )
    return PlacementsReportResponse(
        period_from=start,
        period_to=end,
        currency=currency,
        summary=PlacementsSummary(
            placements=len(records),
            distinct_requisitions=len({r.requisition for r in records}),
            distinct_clients=len({r.client for r in records if r.client}),
            total_ctc=total_ctc,
            total_revenue=total_revenue,
            avg_days_to_fill=avg_days,
        ),
        rows=[
            PlacementRow(
                application_id=r.application_id,
                candidate=r.candidate,
                client=r.client,
                requisition=r.requisition,
                department=r.department,
                consultant=r.consultant,
                joining_date=r.joining_date.date() if hasattr(r.joining_date, "date") else r.joining_date,
                ctc=r.ctc,
                currency=r.currency,
                signing_bonus=r.signing_bonus,
                fee_pct=r.fee_pct,
                revenue=r.revenue,
                days_to_fill=r.days_to_fill,
            )
            for r in records
        ],
    )


def get_client_summary_report_service(
    engine: Engine,
    auth_context: AuthContext,
    period_from: str | None,
    period_to: str | None,
) -> ClientSummaryReportResponse:
    start, end = _resolve_period(period_from, period_to)
    is_admin = auth_context.user.role_code == "admin"
    records = get_client_summary(
        engine, start, end, auth_context.user.location_id, is_admin
    )
    currency = get_dominant_currency(engine)
    return ClientSummaryReportResponse(
        period_from=start,
        period_to=end,
        currency=currency,
        rows=[
            ClientSummaryRow(
                client_id=r.client_id,
                client_name=r.client_name,
                requisitions=r.requisitions,
                open_requisitions=r.open_requisitions,
                placements=r.placements,
                revenue=round(r.revenue, 2),
                avg_days_to_fill=round(r.avg_days_to_fill, 1) if r.avg_days_to_fill else None,
            )
            for r in records
        ],
        totals=ClientSummaryTotals(
            clients=len(records),
            requisitions=sum(r.requisitions for r in records),
            open_requisitions=sum(r.open_requisitions for r in records),
            placements=sum(r.placements for r in records),
            revenue=round(sum(r.revenue for r in records), 2),
        ),
    )
