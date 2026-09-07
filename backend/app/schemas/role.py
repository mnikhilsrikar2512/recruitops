from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.pagination import PaginationMeta

RoleStatus = Literal["active", "inactive"]


class RoleListFilters(BaseModel):
    status: RoleStatus | None = None
    search: str | None = Field(default=None, min_length=1, max_length=100)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    @field_validator("search")
    @classmethod
    def normalize_search(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class RoleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    code: str = Field(min_length=2, max_length=50)
    description: str | None = Field(default=None, max_length=500)
    status: RoleStatus = "active"
    created_by_user_id: int | None = Field(default=None, ge=1)

    @field_validator("name", "description")
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.strip().lower()


class RoleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    status: RoleStatus | None = None

    @field_validator("name", "description")
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @model_validator(mode="after")
    def ensure_any_field_present(self) -> "RoleUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        return self


class RolePermissionsUpdate(BaseModel):
    permission_codes: list[str] = Field(default_factory=list)
    scope_rules: dict[str, str] = Field(default_factory=dict)

    @field_validator("permission_codes")
    @classmethod
    def normalize_permission_codes(cls, values: list[str]) -> list[str]:
        return sorted({value.strip() for value in values if value.strip()})

    @field_validator("scope_rules")
    @classmethod
    def normalize_scope_rules(cls, value: dict[str, str]) -> dict[str, str]:
        normalized: dict[str, str] = {}
        for resource_code, scope_value in value.items():
            key = resource_code.strip()
            current_value = scope_value.strip()
            if key and current_value:
                normalized[key] = current_value
        return normalized


class RoleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    description: str | None
    is_system_role: bool
    status: str
    created_by_user_id: int | None
    created_at: datetime
    updated_at: datetime


class RoleListResponse(BaseModel):
    items: list[RoleResponse]
    meta: PaginationMeta


class RolePermissionsResponse(BaseModel):
    role_id: int
    permission_codes: list[str]
    scope_rules: dict[str, str]

