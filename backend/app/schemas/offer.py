from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.pagination import PaginationMeta

OfferStatus = Literal["draft", "pending-approval", "approved", "sent", "accepted", "declined", "cancelled"]


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


class OfferListFilters(BaseModel):
    location_id: int | None = Field(default=None, ge=1)
    requisition_id: int | None = Field(default=None, ge=1)
    status: OfferStatus | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=25, ge=1, le=100)

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, value: str | None) -> str | None:
        return _normalize_code(value)


class OfferCreate(BaseModel):
    candidate_application_id: int = Field(ge=1)
    offered_ctc: Decimal | None = Field(default=None, ge=0)
    offer_currency: str = Field(default="USD", min_length=1, max_length=10)
    signing_bonus: Decimal | None = Field(default=None, ge=0)
    expected_joining_date: date | None = None
    offer_notes: str | None = Field(default=None, max_length=1000)
    assigned_to_user_id: int | None = Field(default=None, ge=1)
    requested_by_user_id: int | None = Field(default=None, ge=1)

    @field_validator("offer_currency", mode="before")
    @classmethod
    def normalize_currency(cls, value: str | None) -> str:
        normalized = _normalize_text(value)
        return (normalized or "USD").upper()

    @field_validator("offer_notes")
    @classmethod
    def normalize_notes(cls, value: str | None) -> str | None:
        return _normalize_text(value)


class OfferDecisionUpdate(BaseModel):
    status: OfferStatus
    expected_joining_date: date | None = None
    decision_notes: str | None = Field(default=None, max_length=1000)

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, value: str | None) -> str | None:
        return _normalize_code(value)

    @field_validator("decision_notes")
    @classmethod
    def normalize_notes(cls, value: str | None) -> str | None:
        return _normalize_text(value)


class OfferResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    application_id: int
    candidate_id: int
    candidate_name: str
    candidate_email: str | None
    requisition_id: int
    requisition_title: str
    location_id: int
    location_name: str | None
    owner_user_id: int
    owner_name: str | None
    current_stage: str
    application_status: str
    offer_status: str
    offered_ctc: Decimal | None
    offer_currency: str | None
    signing_bonus: Decimal | None
    expected_joining_date: date | None
    offer_notes: str | None
    approval_request_id: int | None
    approval_status: str | None
    requested_by_user_id: int | None
    assigned_to_user_id: int | None
    offer_created_at: datetime | None
    offer_sent_at: datetime | None
    updated_at: datetime


class OfferListResponse(BaseModel):
    items: list[OfferResponse]
    meta: PaginationMeta
