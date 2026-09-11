"""Reports services — orchestration between repository and schemas."""
from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import Engine

from app.repositories.reports import (
    get_report_dataset,
    get_source_effectiveness,
    get_time_to_fill_breakdown,
    get_time_to_fill_summary,
)
from app.schemas.reports import (
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
