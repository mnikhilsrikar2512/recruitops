from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


def _normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()


class AuthUserSummary(BaseModel):
    id: int
    full_name: str
    email: str
    status: str
    business_title: str | None
    phone: str | None = None
    employee_code: str | None = None


class AuthRoleSummary(BaseModel):
    id: int
    code: str
    name: str


class AuthLocationSummary(BaseModel):
    id: int | None
    location_code: str | None
    location_name: str | None
    offers_enabled: bool | None = None


class AuthSessionSummary(BaseModel):
    id: int
    expires_at: datetime
    force_password_change_on_first_login: bool


class LoginResponse(BaseModel):
    token: str
    user: AuthUserSummary
    primary_role: AuthRoleSummary
    primary_location: AuthLocationSummary
    session: AuthSessionSummary


class CurrentSessionResponse(BaseModel):
    user: AuthUserSummary
    primary_role: AuthRoleSummary
    primary_location: AuthLocationSummary


class LogoutResponse(BaseModel):
    message: str


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8, max_length=128)


class PasswordChangeResponse(BaseModel):
    message: str


class ProfileUpdateRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=200)
    phone: str | None = Field(default=None, max_length=30)

    @field_validator("full_name", "phone")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        return _normalize_text(value)

    @model_validator(mode="after")
    def ensure_any_field_present(self) -> "ProfileUpdateRequest":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        # Whitespace-only names normalize to None; treat that as invalid rather than
        # a silent COALESCE no-op that returns 200.
        if "full_name" in self.model_fields_set and self.full_name is None:
            raise ValueError("full_name cannot be empty")
        return self


class PasswordSetupRequest(BaseModel):
    token: str = Field(min_length=1)
    new_password: str = Field(min_length=8, max_length=128)


class PasswordSetupResponse(BaseModel):
    message: str


class PasswordForgotRequest(BaseModel):
    email: EmailStr

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()


class PasswordForgotResponse(BaseModel):
    message: str


class PasswordResetRequest(BaseModel):
    token: str = Field(min_length=1)
    new_password: str = Field(min_length=8, max_length=128)


class PasswordResetResponse(BaseModel):
    message: str
