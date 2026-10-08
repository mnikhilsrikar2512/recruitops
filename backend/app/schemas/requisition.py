from decimal import Decimal
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.pagination import PaginationMeta

RequisitionStatus = Literal["draft", "open", "on-hold", "closed", "cancelled"]
RequisitionPriority = Literal["low", "medium", "high", "critical"]
AssignmentType = Literal["primary_owner", "delivery_owner", "contributor", "support"]


def _normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _normalize_skill_list(values: list[str]) -> list[str]:
    return [item.strip() for item in values if item.strip()]


class RequisitionListFilters(BaseModel):
    # Company the list is restricted to; set from the caller, never from the client.
    tenant_id: int | None = None
    location_id: int | None = Field(default=None, ge=1)
    client_id: int | None = Field(default=None, ge=1)
    primary_owner_user_id: int | None = Field(default=None, ge=1)
    delivery_owner_user_id: int | None = Field(default=None, ge=1)
    status: RequisitionStatus | None = None
    priority: RequisitionPriority | None = None
    due_date_from: str | None = None
    due_date_to: str | None = None
    search: str | None = Field(default=None, min_length=1, max_length=200)
    # Phase 4.9: safe ORDER BY body built from ?sort= via an allowlist (api layer).
    order_by: str = "updated_at DESC, id DESC"
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    @field_validator("search", "due_date_from", "due_date_to")
    @classmethod
    def normalize_fields(cls, value: str | None) -> str | None:
        return _normalize_text(value)


def _check_budget(model):
    if model.currency_code:
        model.currency_code = model.currency_code.strip().upper()
    if model.budget_min is not None and model.budget_max is not None and model.budget_min > model.budget_max:
        raise ValueError("budget_min cannot be more than budget_max")
    return model


class RequisitionCreate(BaseModel):
    client_id: int = Field(ge=1)
    primary_contact_id: int | None = Field(default=None, ge=1)
    secondary_contact_id: int | None = Field(default=None, ge=1)
    location_id: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=200)
    primary_owner_user_id: int = Field(ge=1)
    delivery_owner_user_id: int | None = Field(default=None, ge=1)
    openings_count: int = Field(ge=1)
    priority: RequisitionPriority = "medium"
    target_closure_date: str
    employment_type: str | None = Field(default=None, max_length=50)
    work_mode: str | None = Field(default=None, max_length=50)
    must_have_skills: list[str] = Field(default_factory=list)
    good_to_have_skills: list[str] = Field(default_factory=list)
    acceptable_career_gap_months: int | None = Field(default=None, ge=0)
    profile_update_window_text: str | None = Field(default=None, max_length=100)
    client_round_required: bool = False
    job_description: str = Field(min_length=1)
    stage_template_id: int | None = Field(default=None, ge=1)
    created_by_user_id: int | None = Field(default=None, ge=1)
    # Phase 4.8: pay range for the role; offers above budget_max need approval.
    budget_min: Decimal | None = Field(default=None, ge=0)
    budget_max: Decimal | None = Field(default=None, ge=0)
    currency_code: str | None = Field(default=None, min_length=3, max_length=10)

    @model_validator(mode="after")
    def check_budget(self) -> "RequisitionCreate":
        return _check_budget(self)

    @field_validator("title", "employment_type", "work_mode", "profile_update_window_text", "job_description", "target_closure_date")
    @classmethod
    def normalize_text_fields(cls, value: str | None) -> str | None:
        return _normalize_text(value)

    @field_validator("must_have_skills", "good_to_have_skills")
    @classmethod
    def normalize_skills(cls, value: list[str]) -> list[str]:
        return _normalize_skill_list(value)


class RequisitionUpdate(BaseModel):
    primary_contact_id: int | None = Field(default=None, ge=1)
    secondary_contact_id: int | None = Field(default=None, ge=1)
    title: str | None = Field(default=None, min_length=1, max_length=200)
    primary_owner_user_id: int | None = Field(default=None, ge=1)
    delivery_owner_user_id: int | None = Field(default=None, ge=1)
    openings_count: int | None = Field(default=None, ge=1)
    priority: RequisitionPriority | None = None
    target_closure_date: str | None = None
    employment_type: str | None = Field(default=None, max_length=50)
    work_mode: str | None = Field(default=None, max_length=50)
    must_have_skills: list[str] | None = None
    good_to_have_skills: list[str] | None = None
    acceptable_career_gap_months: int | None = Field(default=None, ge=0)
    profile_update_window_text: str | None = Field(default=None, max_length=100)
    client_round_required: bool | None = None
    job_description: str | None = Field(default=None, min_length=1)
    stage_template_id: int | None = Field(default=None, ge=1)
    # Phase 4.8: pay range for the role; offers above budget_max need approval.
    budget_min: Decimal | None = Field(default=None, ge=0)
    budget_max: Decimal | None = Field(default=None, ge=0)
    currency_code: str | None = Field(default=None, min_length=3, max_length=10)

    @model_validator(mode="after")
    def check_budget(self) -> "RequisitionUpdate":
        return _check_budget(self)

    # Phase 4.3: the version the client loaded; a stale one answers 409.
    version: int | None = Field(default=None, ge=1)

    @field_validator("title", "target_closure_date", "employment_type", "work_mode", "profile_update_window_text", "job_description")
    @classmethod
    def normalize_text_fields(cls, value: str | None) -> str | None:
        return _normalize_text(value)

    @field_validator("must_have_skills", "good_to_have_skills")
    @classmethod
    def normalize_optional_skills(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        return _normalize_skill_list(value)

    @model_validator(mode="after")
    def ensure_any_field_present(self) -> "RequisitionUpdate":
        if not (self.model_fields_set - {"version"}):
            raise ValueError("At least one field must be provided")
        return self


class RequisitionStatusUpdate(BaseModel):
    status: RequisitionStatus
    reason: str = Field(min_length=1, max_length=500)
    # Phase 4.3: the version the client loaded; a stale one answers 409.
    version: int | None = Field(default=None, ge=1)

    @field_validator("reason")
    @classmethod
    def normalize_reason(cls, value: str) -> str:
        return value.strip()


class RequisitionAssignmentCreate(BaseModel):
    assigned_user_id: int = Field(ge=1)
    assignment_type: AssignmentType
    assigned_by_user_id: int | None = Field(default=None, ge=1)


class RequisitionOwnerReassignment(BaseModel):
    new_primary_owner_user_id: int | None = Field(default=None, ge=1)
    new_delivery_owner_user_id: int | None = Field(default=None, ge=1)
    reason: str = Field(min_length=1, max_length=500)
    review_confirmed: bool = False
    changed_by_user_id: int | None = Field(default=None, ge=1)

    @field_validator("reason")
    @classmethod
    def normalize_reason_field(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def ensure_owner_change_present(self) -> "RequisitionOwnerReassignment":
        if self.new_primary_owner_user_id is None and "new_delivery_owner_user_id" not in self.model_fields_set:
            raise ValueError("At least one owner change must be provided")
        return self


class RequisitionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    location_id: int
    requisition_code: str | None
    branch_code: str | None = None
    client_id: int | None
    client_name: str | None
    primary_contact_id: int | None
    primary_contact_name: str | None
    secondary_contact_id: int | None
    secondary_contact_name: str | None
    title: str
    primary_owner_user_id: int
    primary_owner_name: str | None
    delivery_owner_user_id: int | None
    delivery_owner_name: str | None
    priority: str
    status: str
    openings_count: int
    target_closure_date: datetime
    employment_type: str | None
    work_mode: str | None
    acceptable_career_gap_months: int | None
    profile_update_window_text: str | None
    client_round_required: bool
    job_description: str
    stage_template_id: int | None
    must_have_skills: list[str]
    good_to_have_skills: list[str]
    created_at: datetime
    updated_at: datetime
    version: int = 1
    budget_min: float | None = None
    budget_max: float | None = None
    currency_code: str | None = None


class RequisitionListResponse(BaseModel):
    items: list[RequisitionResponse]
    meta: PaginationMeta


class RequisitionAssignmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    location_id: int
    requisition_id: int
    assigned_user_id: int
    assigned_user_name: str | None
    assignment_type: str
    assigned_by_user_id: int
    assigned_by_user_name: str | None
    assigned_at: datetime
    status: str
    created_at: datetime
    updated_at: datetime


class RequisitionOwnerReassignmentResponse(BaseModel):
    requisition_id: int
    previous_primary_owner_user_id: int
    new_primary_owner_user_id: int
    previous_delivery_owner_user_id: int | None
    new_delivery_owner_user_id: int | None
    active_assignment_count: int
    active_application_count: int
    review_required: bool
    reason: str
