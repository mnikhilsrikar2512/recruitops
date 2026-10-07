from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.schemas.pagination import PaginationMeta

CandidateDuplicateState = Literal["not-started", "in-review", "cleared", "merged", "blocked"]
CandidateProfileStatus = Literal["draft", "active", "archived"]
CandidateIntakeStage = Literal["uploaded", "parsed", "needs-review", "duplicate-review", "ready-to-save", "finalized"]
CandidateDocumentStatus = Literal["pending", "verified", "rejected", "not-required"]
CandidateDocumentType = Literal["resume", "aadhar", "pan", "passport", "offer-letter", "payslip", "other"]
CandidateSaveMode = Literal["draft", "final"]
DuplicateDecision = Literal["request_override", "link_existing", "discard_draft"]


def _normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


class SocialProfileInput(BaseModel):
    type: str = Field(min_length=1, max_length=50)
    url: str = Field(min_length=1, max_length=500)

    @field_validator("type", "url")
    @classmethod
    def normalize_text_fields(cls, value: str) -> str:
        return value.strip()


class CandidateListFilters(BaseModel):
    # Set from the caller, never from the client.
    tenant_id: int | None = None
    search: str | None = Field(default=None, min_length=1, max_length=200)
    requisition_id: int | None = Field(default=None, ge=1)
    source_type: str | None = Field(default=None, min_length=1, max_length=50)
    duplicate_state: CandidateDuplicateState | None = None
    owner_user_id: int | None = Field(default=None, ge=1)
    sourced_by_user_id: int | None = Field(default=None, ge=1)
    # Phase 4.4: archived candidates are left out unless asked for (and the
    # caller holds candidate.delete.soft).
    include_archived: bool = False
    # Phase 4.9: safe ORDER BY body built from ?sort= via an allowlist (api layer).
    order_by: str = "updated_at DESC, id DESC"
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    @field_validator("search", "source_type")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        return _normalize_text(value)


class CandidateCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=200)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=30)
    source_type: str = Field(min_length=1, max_length=50)
    source_detail: str | None = Field(default=None, max_length=150)
    current_company: str | None = Field(default=None, max_length=150)
    current_designation: str | None = Field(default=None, max_length=150)
    total_experience_years: float | None = Field(default=None, ge=0, le=99)
    notice_period_days: int | None = Field(default=None, ge=0)
    social_profiles: list[SocialProfileInput] = Field(default_factory=list)
    sourced_by_user_id: int | None = Field(default=None, ge=1)
    primary_owner_user_id: int = Field(ge=1)
    save_mode: CandidateSaveMode = "draft"
    created_by_user_id: int | None = Field(default=None, ge=1)

    @field_validator("full_name", "phone", "source_type", "source_detail", "current_company", "current_designation")
    @classmethod
    def normalize_text_fields(cls, value: str | None) -> str | None:
        return _normalize_text(value)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr | None) -> str | None:
        if value is None:
            return None
        return str(value).strip().lower()


class CandidateUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=200)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=30)
    source_type: str | None = Field(default=None, min_length=1, max_length=50)
    source_detail: str | None = Field(default=None, max_length=150)
    current_company: str | None = Field(default=None, max_length=150)
    current_designation: str | None = Field(default=None, max_length=150)
    total_experience_years: float | None = Field(default=None, ge=0, le=99)
    notice_period_days: int | None = Field(default=None, ge=0)
    social_profiles: list[SocialProfileInput] | None = None
    sourced_by_user_id: int | None = Field(default=None, ge=1)
    primary_owner_user_id: int | None = Field(default=None, ge=1)
    # Phase 4.3: the version the client loaded; a stale one answers 409.
    version: int | None = Field(default=None, ge=1)

    @field_validator("full_name", "phone", "source_type", "source_detail", "current_company", "current_designation")
    @classmethod
    def normalize_text_fields(cls, value: str | None) -> str | None:
        return _normalize_text(value)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr | None) -> str | None:
        if value is None:
            return None
        return str(value).strip().lower()

    @model_validator(mode="after")
    def ensure_any_field_present(self) -> "CandidateUpdate":
        if not (self.model_fields_set - {"version"}):
            raise ValueError("At least one field must be provided")
        return self


class CandidateDocumentCreate(BaseModel):
    document_type: CandidateDocumentType = "other"
    file_name: str = Field(min_length=1, max_length=255)
    file_path: str = Field(min_length=1, max_length=500)
    verification_status: CandidateDocumentStatus = "pending"
    uploaded_by_user_id: int | None = Field(default=None, ge=1)

    @field_validator("file_name", "file_path")
    @classmethod
    def normalize_file_fields(cls, value: str) -> str:
        return value.strip()


class CandidateDuplicateDecisionPayload(BaseModel):
    decision: DuplicateDecision
    matched_candidate_id: int | None = Field(default=None, ge=1)
    decision_notes: str | None = Field(default=None, max_length=1000)
    requested_by_user_id: int | None = Field(default=None, ge=1)
    assigned_reviewer_user_id: int | None = Field(default=None, ge=1)

    @field_validator("decision_notes")
    @classmethod
    def normalize_notes(cls, value: str | None) -> str | None:
        return _normalize_text(value)


class CandidateFinalizePayload(BaseModel):
    requisition_id: int = Field(ge=1)
    initial_stage: str = Field(min_length=1, max_length=50)
    owner_user_id: int = Field(ge=1)
    submitted_by_user_id: int | None = Field(default=None, ge=1)
    finalized_by_user_id: int | None = Field(default=None, ge=1)

    @field_validator("initial_stage")
    @classmethod
    def normalize_stage(cls, value: str) -> str:
        return value.strip()


class CandidateApplicationSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    requisition_id: int
    requisition_title: str | None
    location_id: int
    owner_user_id: int
    owner_name: str | None
    submitted_by_user_id: int | None
    current_stage: str
    application_status: str
    stage_updated_at: datetime
    expected_joining_date: date | None


class CandidateDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    candidate_id: int
    document_type: str
    file_name: str
    file_path: str
    verification_status: str
    uploaded_by_user_id: int
    verified_by_user_id: int | None
    verified_at: datetime | None
    created_at: datetime
    updated_at: datetime
    # Phase 4.2: set for uploads that went through sniff + scan.
    content_type: str | None = None
    size_bytes: int | None = None
    scan_status: str | None = None


class CandidateDuplicateMatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    matched_candidate_id: int
    matched_candidate_name: str
    email: str | None
    phone: str | None
    current_company: str | None
    current_designation: str | None
    duplicate_state: str
    match_score: int
    match_reasons: list[str]
    # Phase 4.7: "exact" (same e-mail/phone, flags for review) or "suggested"
    # (similar name + same location, a hint only).
    match_tier: str = "exact"
    # False for an exact match in another company: contact details withheld.
    in_your_company: bool = True


class CandidateDuplicateReviewCaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    candidate_id: int
    matched_candidate_id: int | None
    decision_status: str
    decision_notes: str | None
    requested_by_user_id: int | None
    assigned_reviewer_user_id: int | None
    created_at: datetime
    updated_at: datetime


class CandidateFootprintEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    application_id: int
    requisition_id: int
    requisition_code: str | None = None
    requisition_title: str | None = None
    client_id: int | None = None
    client_name: str | None = None
    branch_id: int
    branch_code: str | None = None
    current_stage: str
    application_status: str
    stage_updated_at: datetime
    applied_at: datetime


class CandidateFootprintResponse(BaseModel):
    """Admin-only cross-tenant oversight payload. Contains placement context
    only — never notes, offer terms, or owner identities."""

    candidate_id: int
    candidate_code: str | None = None
    full_name: str
    clients_count: int
    entries: list[CandidateFootprintEntry] = Field(default_factory=list)


class CandidateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    candidate_code: str | None
    branch_code: str | None = None
    full_name: str
    email: str | None
    phone: str | None
    current_company: str | None
    current_designation: str | None
    source_type: str | None
    source_detail: str | None
    total_experience_years: float | None
    notice_period_days: int | None
    social_profiles: list[dict[str, Any]]
    sourced_by_user_id: int | None
    sourced_by_name: str | None
    primary_owner_user_id: int | None
    primary_owner_name: str | None
    created_by_user_id: int
    duplicate_state: str
    profile_status: CandidateProfileStatus
    intake_stage: CandidateIntakeStage
    resume_file_name: str | None
    resume_file_path: str | None
    resume_uploaded_at: datetime | None
    finalized_at: datetime | None
    applications: list[CandidateApplicationSummary] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    version: int = 1
    # Phase 4.4: set when the caller's company archived this candidate.
    archived_at: datetime | None = None
    archive_reason: str | None = None


class CandidateListItemResponse(BaseModel):
    id: int
    candidate_code: str | None
    branch_code: str | None = None
    full_name: str
    email: str | None
    phone: str | None
    current_company: str | None
    current_designation: str | None
    source_type: str | None
    source_detail: str | None
    duplicate_state: str
    sourced_by_user_id: int | None
    sourced_by_name: str | None
    primary_owner_user_id: int | None
    primary_owner_name: str | None
    profile_status: str
    intake_stage: str
    applications_count: int
    linked_requisition_titles: list[str]
    updated_at: datetime


class CandidateListResponse(BaseModel):
    items: list[CandidateListItemResponse]
    meta: PaginationMeta


class CandidateDuplicateCheckResponse(BaseModel):
    candidate_id: int
    duplicate_state: str
    matches: list[CandidateDuplicateMatchResponse]


class CandidateFinalizeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    candidate_id: int
    requisition_id: int
    application_id: int
    current_stage: str
    application_status: str
    finalized_at: datetime


class CandidateOwnerReassignment(BaseModel):
    new_primary_owner_user_id: int = Field(ge=1)
    reason: str = Field(min_length=1, max_length=500)
    review_confirmed: bool = False
    changed_by_user_id: int | None = Field(default=None, ge=1)

    @field_validator("reason")
    @classmethod
    def normalize_reassignment_reason(cls, value: str) -> str:
        return value.strip()


class CandidateOwnerReassignmentResponse(BaseModel):
    candidate_id: int
    previous_primary_owner_user_id: int | None
    new_primary_owner_user_id: int
    active_application_count: int
    review_required: bool
    reason: str


class ArchiveRequest(BaseModel):
    """Phase 4.4: archive a candidate or client (reason is kept in history)."""
    reason: str = Field(min_length=3, max_length=500)

    @field_validator("reason")
    @classmethod
    def normalize_reason(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 3:
            raise ValueError("Give a reason of at least 3 characters")
        return normalized


class FileLinkResponse(BaseModel):
    """Phase 4.1: a short-lived download link, issued only after access checks."""
    url: str
    expires_in_seconds: int
    file_name: str
    content_type: str
