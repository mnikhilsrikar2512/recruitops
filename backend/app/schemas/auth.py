from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from app.core.password_policy import validate_new_password


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
    # Access token (JWT) expiry; the refresh token travels in an HttpOnly cookie.
    access_expires_at: datetime | None = None
    # D-09: an Admin who has not enrolled an authenticator is sent to enrolment
    # (enforced when MFA_ENFORCE_ADMIN_ENROLLMENT is on — default in production).
    mfa_enrollment_required: bool = False
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
    new_password: str = Field(min_length=1, max_length=256)

    @field_validator("new_password")
    @classmethod
    def _password_policy(cls, value: str) -> str:
        return validate_new_password(value)


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
    new_password: str = Field(min_length=1, max_length=256)

    @field_validator("new_password")
    @classmethod
    def _password_policy(cls, value: str) -> str:
        return validate_new_password(value)


class PasswordSetupResponse(BaseModel):
    message: str
    # Phase 5.2: the first admin of a company that isn't active yet continues
    # to two-step verification set-up with this token (signup-verify page).
    next: str = "login"
    setup_token: str | None = None


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
    new_password: str = Field(min_length=1, max_length=256)

    @field_validator("new_password")
    @classmethod
    def _password_policy(cls, value: str) -> str:
        return validate_new_password(value)


class PasswordResetResponse(BaseModel):
    message: str


class RefreshResponse(BaseModel):
    token: str
    access_expires_at: datetime


class SessionInfo(BaseModel):
    id: int
    ip_address: str | None = None
    user_agent: str | None = None
    created_at: datetime
    last_seen_at: datetime | None = None
    expires_at: datetime
    current: bool = False


class SessionListResponse(BaseModel):
    items: list[SessionInfo]


class SessionsRevokedResponse(BaseModel):
    revoked: int


class MfaChallengeResponse(BaseModel):
    """Password accepted; a code from the authenticator app is still needed."""
    mfa_required: bool = True
    mfa_token: str
    mfa_expires_at: datetime


class MfaChallengeRequest(BaseModel):
    mfa_token: str = Field(min_length=10)
    code: str | None = Field(default=None, max_length=12)
    recovery_code: str | None = Field(default=None, max_length=20)


class MfaEnrollResponse(BaseModel):
    secret: str
    otpauth_uri: str


class MfaCodeRequest(BaseModel):
    code: str | None = Field(default=None, max_length=12)
    recovery_code: str | None = Field(default=None, max_length=20)


class MfaVerifyResponse(BaseModel):
    enabled: bool
    recovery_codes: list[str]


class MfaStatusResponse(BaseModel):
    enabled: bool
    pending: bool
    required: bool
    recovery_codes_remaining: int
