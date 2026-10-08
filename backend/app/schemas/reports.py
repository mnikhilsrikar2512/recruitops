"""Reports API schemas."""
from datetime import date, datetime
from pydantic import BaseModel, Field


class TimeToFillSummary(BaseModel):
    filled_count: int
    avg_days: float | None
    fastest_days: int | None
    fastest_requisition: str | None
    slowest_days: int | None
    slowest_requisition: str | None
    within_sla: int
    within_sla_percent: float | None


class TimeToFillBreakdown(BaseModel):
    key: str
    label: str
    avg_days: float | None
    filled_count: int


class TimeToFillReportResponse(BaseModel):
    summary: TimeToFillSummary
    by_department: list[TimeToFillBreakdown]
    by_seniority: list[TimeToFillBreakdown]


class SourceEffectivenessRow(BaseModel):
    source: str
    candidates: int
    hired: int
    conversion_rate: float | None
    quality_score: float | None


class SourceEffectivenessReportResponse(BaseModel):
    total_sources: int
    best_source: str | None
    best_source_conversion: float | None
    rows: list[SourceEffectivenessRow]


class ReportColumn(BaseModel):
    key: str
    label: str
    type: str  # "string" | "number" | "date"


class ReportDimension(BaseModel):
    key: str
    label: str
    columns: list[ReportColumn]
    requires: list[str] = Field(default_factory=list)  # permission codes needed


class ReportDatasetResponse(BaseModel):
    dimensions: list[ReportDimension]
    rows: list[dict] = Field(default_factory=list)


class PlacementsSummary(BaseModel):
    placements: int
    distinct_requisitions: int
    distinct_clients: int
    total_ctc: float | None
    total_revenue: float
    avg_days_to_fill: float | None


class PlacementRow(BaseModel):
    application_id: int
    candidate: str
    client: str | None
    requisition: str
    department: str | None
    consultant: str | None
    joining_date: date | None
    ctc: float | None
    currency: str | None
    signing_bonus: float | None
    fee_pct: float | None
    revenue: float
    days_to_fill: int | None


class PlacementsReportResponse(BaseModel):
    period_from: date
    period_to: date
    currency: str | None
    summary: PlacementsSummary
    rows: list[PlacementRow]


class ClientSummaryRow(BaseModel):
    client_id: int
    client_name: str
    requisitions: int
    open_requisitions: int
    placements: int
    revenue: float
    avg_days_to_fill: float | None


class ClientSummaryTotals(BaseModel):
    clients: int
    requisitions: int
    open_requisitions: int
    placements: int
    revenue: float


class ClientSummaryReportResponse(BaseModel):
    period_from: date
    period_to: date
    currency: str | None
    rows: list[ClientSummaryRow]
    totals: ClientSummaryTotals


class WithdrawalReasonRow(BaseModel):
    reason_code: str
    label: str
    withdrawn_count: int
    after_offer_count: int


class WithdrawalReasonsReportResponse(BaseModel):
    """Phase 4.11: why candidates drop out (incl. after an offer)."""
    total: int
    items: list[WithdrawalReasonRow]
