"""Self-serve signup (Phase 5.2)."""
from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.password_policy import validate_new_password


class SignupRequest(BaseModel):
    company_name: str = Field(min_length=2, max_length=150)
    admin_name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)
    city: str | None = Field(default=None, max_length=100)
    # The versions the person saw and accepted on the form (tos, privacy, dpa).
    accepted: dict[str, int]
    # Left empty by people; bots fill every field.
    website: str | None = Field(default=None, max_length=200)

    @field_validator("company_name", "admin_name", "city")
    @classmethod
    def strip(cls, value: str | None) -> str | None:
        return " ".join(value.split()) if value else value

    @field_validator("email")
    @classmethod
    def lower(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("password")
    @classmethod
    def strong(cls, value: str) -> str:
        return validate_new_password(value)


class SignupAccepted(BaseModel):
    message: str
    # Development and CI only (never in staging/production): lets the flow be
    # completed without an email server.
    dev_verify_token: str | None = None


class VerifyRequest(BaseModel):
    token: str = Field(min_length=10, max_length=200)


class VerifyResponse(BaseModel):
    next: str  # "mfa" | "login"
    company_status: str
    setup_token: str | None = None


class ResendRequest(BaseModel):
    email: EmailStr


class SetupTokenRequest(BaseModel):
    setup_token: str = Field(min_length=10)


class MfaConfirmRequest(SetupTokenRequest):
    code: str = Field(min_length=6, max_length=10)


class MfaStartResponse(BaseModel):
    secret: str
    otpauth_uri: str


class MfaConfirmResponse(BaseModel):
    recovery_codes: list[str]
    company_status: str
    next: str = "login"
