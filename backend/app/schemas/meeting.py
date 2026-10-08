from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.pagination import PaginationMeta

MeetingType = Literal[
    "client_introduction",
    "requirement_discussion",
    "follow_up",
    "review_meeting",
    "escalation_meeting",
    "internal_review",
]
MeetingAttendanceStatus = Literal["pending", "attended", "partially-attended", "no-show", "cancelled"]
MeetingOutcomeStatus = Literal["pending", "accepted", "rejected", "follow-up-required", "rescheduled", "closed"]
MeetingAttendeeType = Literal["internal-user", "client-contact"]


def _normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _normalize_code(value: str | None) -> str | None:
    normalized = _normalize_text(value)
    if normalized is None:
        return None
    return normalized.lower().replace("_", "-").replace(" ", "-")


def _normalize_meeting_type_code(value: str | None) -> str | None:
    normalized = _normalize_text(value)
    if normalized is None:
        return None
    return normalized.lower().replace("-", "_").replace(" ", "_")


class MeetingListFilters(BaseModel):
    # Company the list is restricted to; set from the caller, never from the client.
    tenant_id: int | None = None
    location_id: int | None = Field(default=None, ge=1)
    client_id: int | None = Field(default=None, ge=1)
    meeting_owner_user_id: int | None = Field(default=None, ge=1)
    outcome_status: MeetingOutcomeStatus | None = None
    attendance_status: MeetingAttendanceStatus | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class MeetingCreate(BaseModel):
    location_id: int = Field(ge=1)
    client_id: int = Field(ge=1)
    end_client_id: int | None = Field(default=None, ge=1)
    meeting_owner_user_id: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=200)
    meeting_type: MeetingType
    scheduled_at: datetime | None = None
    agenda: str | None = None
    follow_up_owner_user_id: int | None = Field(default=None, ge=1)
    follow_up_due_date: date | None = None

    @field_validator("title", "agenda")
    @classmethod
    def normalize_text_fields(cls, value: str | None) -> str | None:
        return _normalize_text(value)

    @field_validator("meeting_type", mode="before")
    @classmethod
    def normalize_meeting_type(cls, value: str) -> str:
        return _normalize_meeting_type_code(value) or value


class MeetingUpdate(BaseModel):
    attendance_status: MeetingAttendanceStatus | None = None
    outcome_status: MeetingOutcomeStatus | None = None
    minutes_of_meeting: str | None = Field(default=None, max_length=4000)
    decision_summary: str | None = Field(default=None, max_length=4000)
    next_steps: str | None = Field(default=None, max_length=4000)
    follow_up_owner_user_id: int | None = Field(default=None, ge=1)
    follow_up_due_date: date | None = None

    @field_validator("attendance_status", "outcome_status", mode="before")
    @classmethod
    def normalize_status_codes(cls, value: str | None) -> str | None:
        return _normalize_code(value)

    @field_validator("minutes_of_meeting", "decision_summary", "next_steps")
    @classmethod
    def normalize_text_fields(cls, value: str | None) -> str | None:
        return _normalize_text(value)

    @model_validator(mode="after")
    def ensure_any_field_present(self) -> "MeetingUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        return self


class MeetingAttendeeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    meeting_id: int
    attendee_type: str
    user_id: int | None
    user_name: str | None
    client_contact_id: int | None
    client_contact_name: str | None
    attendance_status: str
    notes: str | None
    created_at: datetime
    updated_at: datetime


class MeetingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    location_id: int
    location_name: str | None
    client_id: int
    client_name: str | None
    end_client_id: int | None
    end_client_name: str | None
    meeting_owner_user_id: int
    meeting_owner_name: str | None
    title: str
    meeting_type: str
    scheduled_at: datetime | None
    attendance_status: str
    outcome_status: str
    agenda: str | None
    minutes_of_meeting: str | None
    decision_summary: str | None
    next_steps: str | None
    follow_up_owner_user_id: int | None
    follow_up_owner_name: str | None
    follow_up_due_date: date | None
    attendees: list[MeetingAttendeeResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class MeetingListResponse(BaseModel):
    items: list[MeetingResponse]
    meta: PaginationMeta
