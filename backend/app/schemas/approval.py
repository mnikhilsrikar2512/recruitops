from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.pagination import PaginationMeta

ApprovalType = Literal["requisition", "offer", "exception", "change_request"]
ApprovalStatus = Literal["pending", "approved", "rejected", "cancelled"]
ApprovalPriority = Literal["critical", "high", "standard"]


def _normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _normalize_code(value: str | None) -> str | None:
    normalized = _normalize_text(value)
    if normalized is None:
        return None
    return normalized.lower().replace(" ", "_")


class ApprovalListFilters(BaseModel):
    location_id: int | None = Field(default=None, ge=1)
    approval_type: str | None = Field(default=None, min_length=1, max_length=50)
    status: str | None = Field(default=None, min_length=1, max_length=20)
    priority: str | None = Field(default=None, min_length=1, max_length=20)
    requester_user_id: int | None = Field(default=None, ge=1)
    assigned_reviewer_user_id: int | None = Field(default=None, ge=1)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class ApprovalCreate(BaseModel):
    location_id: int = Field(ge=1)
    approval_type: str = Field(min_length=1, max_length=50)
    related_entity_type: str = Field(min_length=1, max_length=50)
    related_entity_id: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    priority: str = Field(default="standard", max_length=20)
    requester_user_id: int = Field(ge=1)
    assigned_reviewer_user_id: int | None = Field(default=None, ge=1)
    sla_deadline: datetime | None = None

    @field_validator("title", "description")
    @classmethod
    def normalize_text_fields(cls, value: str | None) -> str | None:
        return _normalize_text(value)

    @field_validator("approval_type", "related_entity_type", "priority", mode="before")
    @classmethod
    def normalize_code_fields(cls, value: str) -> str:
        return _normalize_code(value) or value


class ApprovalDecision(BaseModel):
    decision: str = Field(min_length=1, max_length=20)  # 'approved' or 'rejected'
    decision_notes: str | None = Field(default=None, max_length=1000)
    decision_user_id: int = Field(ge=1)

    @field_validator("decision")
    @classmethod
    def normalize_decision(cls, value: str) -> str:
        return _normalize_code(value) or value

    @field_validator("decision_notes")
    @classmethod
    def normalize_notes(cls, value: str | None) -> str | None:
        return _normalize_text(value)


class ApprovalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    location_id: int
    location_name: str | None
    approval_type: str
    related_entity_type: str
    related_entity_id: int
    title: str
    description: str | None
    priority: str
    status: str
    requester_user_id: int
    requester_name: str | None
    assigned_reviewer_user_id: int | None
    assigned_reviewer_name: str | None
    decision_user_id: int | None
    decision_user_name: str | None
    decision_at: datetime | None
    decision_notes: str | None
    sla_deadline: datetime | None
    created_at: datetime
    updated_at: datetime


class ApprovalListResponse(BaseModel):
    items: list[ApprovalResponse]
    meta: PaginationMeta
