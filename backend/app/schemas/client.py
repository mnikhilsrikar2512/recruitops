from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.schemas.pagination import PaginationMeta

ClientStatus = Literal["active", "inactive", "prospect"]
ClientContactStatus = Literal["active", "inactive"]


class ClientListFilters(BaseModel):
    # Company the list is restricted to; set from the caller, never from the client.
    tenant_id: int | None = None
    location_id: int | None = Field(default=None, ge=1)
    status: ClientStatus | None = None
    client_owner_user_id: int | None = Field(default=None, ge=1)
    business_source_owner_user_id: int | None = Field(default=None, ge=1)
    search: str | None = Field(default=None, min_length=1, max_length=200)
    # Phase 4.4: archived clients are left out unless asked for.
    include_archived: bool = False
    # Phase 4.9: safe ORDER BY body built from ?sort= via an allowlist (api layer).
    order_by: str = "updated_at DESC, id DESC"
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    @field_validator("search")
    @classmethod
    def normalize_search(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class ClientCreate(BaseModel):
    client_name: str = Field(min_length=1, max_length=200)
    client_code: str | None = Field(default=None, max_length=50)
    location_id: int = Field(ge=1)
    industry: str | None = Field(default=None, max_length=100)
    client_owner_user_id: int = Field(ge=1)
    business_source_owner_user_id: int = Field(ge=1)
    placement_fee_pct: float | None = Field(default=None, ge=0, le=100)
    status: ClientStatus = "active"
    notes: str | None = None
    created_by_user_id: int | None = Field(default=None, ge=1)

    @field_validator("client_name", "industry", "notes")
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("client_code")
    @classmethod
    def normalize_code(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().upper()
        return normalized or None


class ClientUpdate(BaseModel):
    client_name: str | None = Field(default=None, min_length=1, max_length=200)
    industry: str | None = Field(default=None, max_length=100)
    client_owner_user_id: int | None = Field(default=None, ge=1)
    business_source_owner_user_id: int | None = Field(default=None, ge=1)
    placement_fee_pct: float | None = Field(default=None, ge=0, le=100)
    status: ClientStatus | None = None
    notes: str | None = None
    # Phase 4.13: true/false overrides the company; null = use the company setting
    offers_signing_bonus: bool | None = None
    bonus_counts_against_budget: bool | None = None

    @field_validator("client_name", "industry", "notes")
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @model_validator(mode="after")
    def ensure_any_field_present(self) -> "ClientUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        return self


class ClientContactCreate(BaseModel):
    contact_name: str = Field(min_length=1, max_length=200)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=30)
    designation: str | None = Field(default=None, max_length=150)
    is_primary_contact: bool = False
    is_secondary_contact: bool = False
    notes: str | None = None
    status: ClientContactStatus = "active"
    created_by_user_id: int | None = Field(default=None, ge=1)

    @field_validator("contact_name", "phone", "designation", "notes")
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr | None) -> str | None:
        if value is None:
            return None
        return str(value).strip().lower()


class ClientContactUpdate(BaseModel):
    contact_name: str | None = Field(default=None, min_length=1, max_length=200)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=30)
    designation: str | None = Field(default=None, max_length=150)
    is_primary_contact: bool | None = None
    is_secondary_contact: bool | None = None
    notes: str | None = None
    status: ClientContactStatus | None = None

    @field_validator("contact_name", "phone", "designation", "notes")
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr | None) -> str | None:
        if value is None:
            return None
        return str(value).strip().lower()

    @model_validator(mode="after")
    def ensure_any_field_present(self) -> "ClientContactUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        return self


class ClientResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    location_id: int
    client_code: str | None
    client_name: str
    industry: str | None
    status: str
    business_source_owner_user_id: int | None
    business_source_owner_name: str | None
    client_owner_user_id: int | None
    client_owner_name: str | None
    placement_fee_pct: float | None
    notes: str | None
    created_by_user_id: int | None
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None = None
    archive_reason: str | None = None
    offers_signing_bonus: bool | None = None
    bonus_counts_against_budget: bool | None = None


class ClientListResponse(BaseModel):
    items: list[ClientResponse]
    meta: PaginationMeta


class ClientContactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    client_id: int
    location_id: int | None
    contact_name: str
    designation: str | None
    email: str | None
    phone: str | None
    is_primary_contact: bool
    is_secondary_contact: bool
    status: str
    notes: str | None
    created_by_user_id: int | None
    created_at: datetime
    updated_at: datetime

