"""Reports API schemas."""
from datetime import datetime
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
