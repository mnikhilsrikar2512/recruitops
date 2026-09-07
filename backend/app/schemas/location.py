from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.pagination import PaginationMeta

LocationStatus = Literal["active", "inactive", "planned"]


class LocationBase(BaseModel):
    location_name: str = Field(min_length=1, max_length=150)
    address: str | None = Field(default=None, max_length=500)
    status: LocationStatus = "active"
    location_head_user_id: int | None = Field(default=None, ge=1)

    @field_validator("location_name")
    @classmethod
    def normalize_location_name(cls, value: str) -> str:
        return value.strip()

    @field_validator("address")
    @classmethod
    def normalize_address(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class LocationCreate(LocationBase):
    location_code: str = Field(min_length=2, max_length=50)

    @field_validator("location_code")
    @classmethod
    def normalize_location_code(cls, value: str) -> str:
        return value.strip().upper()


class LocationUpdate(BaseModel):
    location_name: str | None = Field(default=None, min_length=1, max_length=150)
    address: str | None = Field(default=None, max_length=500)
    status: LocationStatus | None = None
    location_head_user_id: int | None = Field(default=None, ge=1)

    @field_validator("location_name")
    @classmethod
    def normalize_location_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip()

    @field_validator("address")
    @classmethod
    def normalize_address(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @model_validator(mode="after")
    def ensure_any_field_present(self) -> "LocationUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        return self


class LocationListFilters(BaseModel):
    status: LocationStatus | None = None
    search: str | None = Field(default=None, min_length=1, max_length=150)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    @field_validator("search")
    @classmethod
    def normalize_search(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class LocationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    location_name: str
    location_code: str
    address: str | None
    status: str
    location_head_user_id: int | None
    location_head_name: str | None
    created_at: datetime
    updated_at: datetime


class LocationListResponse(BaseModel):
    items: list[LocationResponse]
    meta: PaginationMeta

