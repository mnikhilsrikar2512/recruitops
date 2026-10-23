from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.schemas.pagination import PaginationMeta

UserStatus = Literal["active", "inactive", "suspended", "pending"]
ResetMode = Literal["temporary-password", "setup-link"]


class UserListFilters(BaseModel):
    # Company the list is restricted to; set from the caller, never from the client.
    tenant_id: int | None = None
    location_id: int | None = Field(default=None, ge=1)
    role_id: int | None = Field(default=None, ge=1)
    status: UserStatus | None = None
    search: str | None = Field(default=None, min_length=1, max_length=200)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    @field_validator("search")
    @classmethod
    def normalize_search(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class UserCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=30)
    employee_code: str = Field(min_length=1, max_length=50)
    primary_location_id: int = Field(ge=1)
    primary_role_id: int = Field(ge=1)
    reporting_manager_user_id: int | None = Field(default=None, ge=1)
    business_title: str | None = Field(default=None, max_length=100)
    status: UserStatus = "active"
    created_by_user_id: int | None = Field(default=None, ge=1)

    @field_validator("full_name", "employee_code", "phone", "business_title")
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=200)
    phone: str | None = Field(default=None, max_length=30)
    primary_location_id: int | None = Field(default=None, ge=1)
    primary_role_id: int | None = Field(default=None, ge=1)
    reporting_manager_user_id: int | None = Field(default=None, ge=1)
    business_title: str | None = Field(default=None, max_length=100)
    status: UserStatus | None = None

    @field_validator("full_name", "phone", "business_title")
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @model_validator(mode="after")
    def ensure_any_field_present(self) -> "UserUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        return self


class UserResetCredentials(BaseModel):
    mode: ResetMode
    issued_by_user_id: int | None = Field(default=None, ge=1)


class UserDeactivateRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)
    review_confirmed: bool = False
    transfer_to_user_id: int | None = Field(default=None, ge=1)
    changed_by_user_id: int | None = Field(default=None, ge=1)

    @field_validator("reason")
    @classmethod
    def normalize_reason(cls, value: str) -> str:
        return value.strip()


class UserDeactivationResponse(BaseModel):
    user_id: int
    previous_status: str
    new_status: str
    transfer_to_user_id: int | None
    review_required: bool
    active_requisition_count: int
    active_assignment_count: int
    active_candidate_owner_count: int
    active_pipeline_owner_count: int
    reason: str


class UserMoveRequest(BaseModel):
    new_primary_location_id: int | None = Field(default=None, ge=1)
    new_primary_role_id: int | None = Field(default=None, ge=1)
    reason: str = Field(min_length=1, max_length=500)
    review_confirmed: bool = False
    transfer_to_user_id: int | None = Field(default=None, ge=1)
    changed_by_user_id: int | None = Field(default=None, ge=1)

    @field_validator("reason")
    @classmethod
    def normalize_move_reason(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def ensure_move_target_present(self) -> "UserMoveRequest":
        if self.new_primary_location_id is None and self.new_primary_role_id is None:
            raise ValueError("At least one move target must be provided")
        return self


class UserMoveResponse(BaseModel):
    user_id: int
    previous_primary_location_id: int | None
    new_primary_location_id: int | None
    previous_primary_role_id: int
    new_primary_role_id: int
    transfer_to_user_id: int | None
    review_required: bool
    active_requisition_count: int
    active_assignment_count: int
    active_candidate_owner_count: int
    active_pipeline_owner_count: int
    reason: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: str
    phone: str | None
    employee_code: str | None
    status: str
    business_title: str | None
    primary_location_id: int | None
    primary_location_name: str | None
    primary_role_id: int
    primary_role_name: str
    reporting_manager_user_id: int | None
    reporting_manager_name: str | None
    password_setup_status: str
    force_password_change_on_first_login: bool
    created_at: datetime
    updated_at: datetime


class UserListResponse(BaseModel):
    items: list[UserResponse]
    meta: PaginationMeta


class UserResetCredentialsResponse(BaseModel):
    user_id: int
    mode: ResetMode
    password_setup_status: str
    temporary_password: str | None = None
    setup_token: str | None = None
    expires_in_hours: int | None = None
    message: str | None = None
    errors: list[str] | None = None


class UserExtraPermissionsUpdate(BaseModel):
    """Replace-all set of extra permission codes granted directly to a user,
    on top of their role. Empty list clears all extra grants."""

    permission_codes: list[str] = Field(default_factory=list)

    @field_validator("permission_codes")
    @classmethod
    def normalize_permission_codes(cls, values: list[str]) -> list[str]:
        return sorted({value.strip() for value in values if value.strip()})


class UserExtraPermissionsResponse(BaseModel):
    user_id: int
    permission_codes: list[str]
