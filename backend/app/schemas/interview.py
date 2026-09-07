from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator, field_validator

from app.schemas.pagination import PaginationMeta

InterviewRoundType = Literal["internal", "manager", "client"]
InterviewStatus = Literal["scheduled", "completed", "rescheduled", "cancelled", "no-show"]
InterviewDecision = Literal["strong-yes", "yes", "no", "strong-no", "clear", "selected", "rejected", "hold"]


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


class InterviewListFilters(BaseModel):
    candidate_application_id: int | None = Field(default=None, ge=1)
    location_id: int | None = Field(default=None, ge=1)
    interviewer_user_id: int | None = Field(default=None, ge=1)
    status: InterviewStatus | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=25, ge=1, le=100)

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, value: str | None) -> str | None:
        return _normalize_code(value)


class InterviewCreate(BaseModel):
    candidate_application_id: int = Field(ge=1)
    round_type: InterviewRoundType
    round_name: str = Field(min_length=1, max_length=100)
    scheduled_at: datetime | None = None
    interviewer_name: str | None = Field(default=None, max_length=200)
    interviewer_user_id: int | None = Field(default=None, ge=1)
    status: InterviewStatus = "scheduled"
    created_by_user_id: int | None = Field(default=None, ge=1)

    @field_validator("round_type", "status", mode="before")
    @classmethod
    def normalize_codes(cls, value: str | None) -> str | None:
        return _normalize_code(value)

    @field_validator("round_name", "interviewer_name")
    @classmethod
    def normalize_text_fields(cls, value: str | None) -> str | None:
        return _normalize_text(value)


class InterviewFeedbackUpdate(BaseModel):
    status: InterviewStatus = "completed"
    feedback_status: str = Field(default="received", min_length=1, max_length=30)
    decision: InterviewDecision | None = None
    feedback_notes: str | None = Field(default=None, max_length=1000)

    @field_validator("status", "feedback_status", "decision", mode="before")
    @classmethod
    def normalize_codes(cls, value: str | None) -> str | None:
        return _normalize_code(value)

    @field_validator("feedback_notes")
    @classmethod
    def normalize_notes(cls, value: str | None) -> str | None:
        return _normalize_text(value)

    @model_validator(mode="after")
    def require_feedback_signal(self) -> "InterviewFeedbackUpdate":
        if not self.decision and not self.feedback_notes:
            raise ValueError("Feedback requires a decision or notes")
        return self


class InterviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    candidate_application_id: int
    candidate_id: int
    candidate_name: str
    requisition_id: int
    requisition_title: str
    location_id: int
    location_name: str | None
    round_type: str
    round_name: str
    scheduled_at: datetime | None
    interviewer_name: str | None
    interviewer_user_id: int | None
    status: str
    feedback_status: str | None
    decision: str | None
    feedback_notes: str | None
    created_by_user_id: int
    created_by_name: str | None
    created_at: datetime
    updated_at: datetime


class InterviewListResponse(BaseModel):
    items: list[InterviewResponse]
    meta: PaginationMeta
