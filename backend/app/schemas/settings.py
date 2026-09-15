"""Company settings schemas — the letterhead source of truth for reports."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

CompanyTypeCode = Literal["recruitment-agency", "staffing", "consulting", "other"]


class CompanyProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    display_name: str
    legal_name: str
    company_code: str
    company_type_code: str | None
    hq_city: str | None
    hq_state: str | None
    country_name: str | None
    support_email: str | None
    support_phone: str | None
    website_url: str | None
    registered_address: str | None
    has_logo: bool


class CompanyProfileUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=200)
    legal_name: str | None = Field(default=None, min_length=1, max_length=250)
    company_type_code: CompanyTypeCode | None = None
    hq_city: str | None = Field(default=None, max_length=100)
    hq_state: str | None = Field(default=None, max_length=100)
    country_name: str | None = Field(default=None, max_length=100)
    support_email: str | None = Field(default=None, max_length=255)
    support_phone: str | None = Field(default=None, max_length=50)
    website_url: str | None = Field(default=None, max_length=255)
    registered_address: str | None = Field(default=None, max_length=1000)

    @field_validator("*")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @model_validator(mode="after")
    def ensure_any_field_present(self) -> "CompanyProfileUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        return self


class CompanyLogoUpdate(BaseModel):
    data_url: str = Field(min_length=1)

    @field_validator("data_url")
    @classmethod
    def validate_data_url(cls, value: str) -> str:
        value = value.strip()
        if not value.startswith("data:image/"):
            raise ValueError("data_url must be an image data URL (data:image/...)")
        if len(value) > 400_000:
            raise ValueError("Logo image too large (max ~300KB encoded)")
        return value


class CompanyLogoResponse(BaseModel):
    logo_url: str | None
