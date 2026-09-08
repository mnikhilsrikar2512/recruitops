from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.pagination import PaginationMeta

DailyUpdateSubmissionStatus = Literal["draft", "submitted", "reviewed"]


def _normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


class DailyUpdateListFilters(BaseModel):
    location_id: int | None = Field(default=None, ge=1)
    user_id: int | None = Field(default=None, ge=1)
    requisition_id: int | None = Field(default=None, ge=1)
    update_date: date | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class DailyUpdateCreate(BaseModel):
    update_date: date
    requisition_id: int = Field(ge=1)
    submitted_by_user_id: int | None = Field(default=None, ge=1)
    summary: str = Field(min_length=1)
    profiles_sourced_count: int | None = Field(default=None, ge=0)
    profiles_screened_count: int | None = Field(default=None, ge=0)
    profiles_submitted_count: int | None = Field(default=None, ge=0)
    interviews_scheduled_count: int | None = Field(default=None, ge=0)
    offers_closed_count: int | None = Field(default=None, ge=0)
    blockers: str | None = None
    next_actions: str | None = None
    submission_status: DailyUpdateSubmissionStatus = "submitted"

    @field_validator("summary", "blockers", "next_actions")
    @classmethod
    def normalize_text_fields(cls, value: str | None) -> str | None:
        return _normalize_text(value)


class DailyUpdateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    location_id: int
    submitted_by_user_id: int
    submitted_by_name: str | None
    requisition_id: int | None
    requisition_title: str | None
    update_date: date
    summary: str
    profiles_sourced_count: int | None
    profiles_screened_count: int | None
    profiles_submitted_count: int | None
    interviews_scheduled_count: int | None
    offers_closed_count: int | None
    blockers: str | None
    next_actions: str | None
    submission_status: str
    submitted_at: datetime
    created_at: datetime
    updated_at: datetime


class DailyUpdateListResponse(BaseModel):
    items: list[DailyUpdateResponse]
    meta: PaginationMeta
