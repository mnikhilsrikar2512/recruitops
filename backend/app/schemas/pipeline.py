from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.withdrawal import WithdrawalReason


def _normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


class PipelineBoardFilters(BaseModel):
    # Company the list is restricted to; set from the caller, never from the client.
    tenant_id: int | None = None
    requisition_id: int | None = Field(default=None, ge=1)
    owner_user_id: int | None = Field(default=None, ge=1)
    sourced_by_user_id: int | None = Field(default=None, ge=1)
    stage: str | None = Field(default=None, min_length=1, max_length=50)
    location_id: int | None = Field(default=None, ge=1)

    @field_validator("stage")
    @classmethod
    def normalize_stage(cls, value: str | None) -> str | None:
        return _normalize_text(value)


class PipelineStageMove(BaseModel):
    to_stage: str = Field(min_length=1, max_length=50)
    notes: str | None = Field(default=None, max_length=1000)
    rejection_reason: str | None = Field(default=None, max_length=1000)
    joining_date: date | None = None
    changed_by_user_id: int | None = Field(default=None, ge=1)
    # Phase 4.11: why the candidate withdrew ("no_reason_given" is fine).
    withdrawal_reason: WithdrawalReason | None = None
    # Phase 4.3: the version the client loaded; a stale one answers 409.
    version: int | None = Field(default=None, ge=1)

    @field_validator("to_stage", "notes", "rejection_reason")
    @classmethod
    def normalize_text_fields(cls, value: str | None) -> str | None:
        return _normalize_text(value)


class PipelineReopen(BaseModel):
    to_stage: str = Field(min_length=1, max_length=50)
    reason: str = Field(min_length=3, max_length=1000)
    # Phase 4.3: the version the client loaded; a stale one answers 409.
    version: int | None = Field(default=None, ge=1)

    @field_validator("to_stage", "reason")
    @classmethod
    def normalize_text_fields(cls, value: str) -> str:
        normalized = _normalize_text(value)
        if normalized is None:
            raise ValueError("must not be blank")
        return normalized


class PipelineBoardItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    application_id: int
    candidate_id: int
    candidate_name: str
    requisition_id: int
    requisition_title: str
    requisition_code: str | None = None
    candidate_code: str | None = None
    branch_code: str | None = None
    location_id: int
    location_name: str | None
    owner_user_id: int
    owner_name: str | None
    sourced_by_user_id: int | None
    sourced_by_name: str | None
    current_stage: str
    application_status: str
    stage_updated_at: datetime
    last_activity_at: datetime | None
    expected_joining_date: date | None


class PipelineApplicationDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    application_id: int
    candidate_id: int
    candidate_name: str
    requisition_id: int
    requisition_title: str
    requisition_code: str | None = None
    candidate_code: str | None = None
    branch_code: str | None = None
    location_id: int
    location_name: str | None
    owner_user_id: int
    owner_name: str | None
    sourced_by_user_id: int | None
    sourced_by_name: str | None
    submitted_by_user_id: int | None
    submitted_by_name: str | None
    current_stage: str
    application_status: str
    screening_status: str
    stage_reason: str | None
    rejection_side: str
    rejection_stage: str | None
    rejection_reason: str | None
    client_feedback_status: str | None
    client_feedback_notes: str | None
    stage_updated_at: datetime
    last_activity_at: datetime | None
    expected_joining_date: date | None
    applied_at: datetime
    updated_at: datetime
    version: int = 1
    withdrawal_reason: str | None = None
    offer_status: str | None = None
    requisition_status: str | None = None


class PipelineStageMoveResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    application_id: int
    from_stage: str
    to_stage: str
    application_status: str
    stage_updated_at: datetime
    version: int | None = None


class PipelineHistoryItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    candidate_application_id: int
    from_stage: str | None
    to_stage: str
    change_reason: str | None
    changed_by_user_id: int
    changed_by_name: str | None
    changed_at: datetime
    source_type: str
