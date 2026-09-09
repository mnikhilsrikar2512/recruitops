from datetime import date, datetime, time
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.pagination import PaginationMeta

PortalAccountStatus = Literal["active", "inactive", "locked"]
OwnershipType = Literal["company-shared", "user-owned", "client-owned"]
SlotStatus = Literal["planned", "approved", "completed", "expired", "cancelled"]

PORTAL_STATUS_VALUES = ("active", "inactive", "locked")
OWNERSHIP_TYPE_VALUES = ("company-shared", "user-owned", "client-owned")
SLOT_STATUS_VALUES = ("planned", "completed", "cancelled")


def _normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


class PortalAccountBase(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=False)

    platform_name: str = Field(min_length=1, max_length=100)
    account_name: str = Field(min_length=1, max_length=150)
    login_identifier: str | None = Field(default=None, max_length=255)
    status: PortalAccountStatus = "active"
    ownership_type: OwnershipType
    owned_by_user_id: int | None = Field(default=None, ge=1)
    is_shared: bool = True
    has_full_access: bool = False
    daily_usage_limit_hours: float | None = Field(default=None, ge=0, le=24)
    notes: str | None = Field(default=None, max_length=4000)

    @field_validator("platform_name", "account_name")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("login_identifier", "notes")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        return _normalize_text(value)


class PortalAccountCreate(PortalAccountBase):
    branch_id: int = Field(ge=1)
    owned_by_user_id: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def validate_ownership(self) -> "PortalAccountCreate":
        if self.ownership_type == "user-owned" and not self.owned_by_user_id:
            raise ValueError("user-owned accounts require owned_by_user_id")
        return self


class PortalAccountUpdate(BaseModel):
    platform_name: str | None = Field(default=None, min_length=1, max_length=100)
    account_name: str | None = Field(default=None, min_length=1, max_length=150)
    login_identifier: str | None = Field(default=None, max_length=255)
    status: PortalAccountStatus | None = None
    ownership_type: OwnershipType | None = None
    owned_by_user_id: int | None = Field(default=None, ge=1)
    is_shared: bool | None = None
    has_full_access: bool | None = None
    daily_usage_limit_hours: float | None = Field(default=None, ge=0, le=24)
    notes: str | None = Field(default=None, max_length=4000)

    @field_validator("platform_name", "account_name")
    @classmethod
    def normalize_required_text(cls, value: str | None) -> str | None:
        return _normalize_text(value)

    @field_validator("login_identifier", "notes")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        return _normalize_text(value)


class PortalAccountResponse(PortalAccountBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    branch_id: int
    branch_name: str | None = None
    owned_by_user_name: str | None = None
    created_at: datetime
    updated_at: datetime


class PortalAccountListFilters(BaseModel):
    status: str | None = None
    platform: str | None = None
    ownership_type: str | None = None
    search: str | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class PortalAccountListResponse(BaseModel):
    items: list[PortalAccountResponse]
    meta: PaginationMeta


class PortalSlotBase(BaseModel):
    assigned_user_id: int = Field(ge=1)
    usage_date: date
    start_time: time
    end_time: time
    status: SlotStatus = "planned"
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator("notes")
    @classmethod
    def normalize_notes(cls, value: str | None) -> str | None:
        return _normalize_text(value)

    @model_validator(mode="after")
    def validate_time_window(self) -> "PortalSlotBase":
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time")
        return self


class PortalSlotCreate(PortalSlotBase):
    pass


class PortalSlotUpdate(BaseModel):
    assigned_user_id: int | None = Field(default=None, ge=1)
    usage_date: date | None = None
    start_time: time | None = None
    end_time: time | None = None
    status: SlotStatus | None = None
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator("notes")
    @classmethod
    def normalize_notes(cls, value: str | None) -> str | None:
        return _normalize_text(value)


class PortalSlotListFilters(BaseModel):
    status: str | None = None
    usage_date: date | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=200)


class PortalSlotResponse(PortalSlotBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    portal_account_id: int
    assigned_user_name: str | None = None
    approved_by_user_name: str | None = None
    created_at: datetime
    updated_at: datetime


class PortalSlotListResponse(BaseModel):
    items: list[PortalSlotResponse]
    meta: PaginationMeta


class PortalAvailabilityFilters(BaseModel):
    platform: str | None = None
    branch_id: int | None = Field(default=None, ge=1)
    usage_date: date | None = None


class PortalAvailabilityEntry(BaseModel):
    portal_account_id: int
    platform_name: str
    account_name: str
    branch_name: str | None = None
    is_shared: bool
    has_full_access: bool
    daily_usage_limit_hours: float | None = None
    booked_minutes: int = 0


class PortalAvailabilityResponse(BaseModel):
    items: list[PortalAvailabilityEntry]


class PortalWeeklyUsageEntry(BaseModel):
    """Booked hours for one platform across ISO weeks (most recent last)."""

    platform_name: str
    weeks: list["PortalWeeklyBucket"]
    total_hours: float = 0


class PortalWeeklyBucket(BaseModel):
    week_start: date
    booked_hours: float = 0


class PortalWeeklyUsageResponse(BaseModel):
    weeks: list[date]
    platforms: list[PortalWeeklyUsageEntry]
