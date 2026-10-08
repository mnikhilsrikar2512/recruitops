"""Privacy requests (Phase 5.3)."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class PrivacyRequestResponse(BaseModel):
    id: int
    tenant_id: int
    request_type: str
    candidate_id: int | None = None
    status: str
    reason: str | None = None
    requested_by_user_id: int
    requested_by_name: str | None = None
    requested_at: datetime
    approval_id: int | None = None
    approved_by_user_id: int | None = None
    approved_at: datetime | None = None
    approval_method: str | None = None
    execute_after: datetime | None = None
    cancelled_by_user_id: int | None = None
    cancelled_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    result_bytes: int | None = None
    result_expires_at: datetime | None = None
    summary: Any = None
    error: str | None = None
    download_ready: bool = False
    needs_self_confirmation: bool | None = None


class CompanyDeleteRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=1000)
    confirm: str = Field(min_length=1, max_length=50)

    @field_validator("confirm")
    @classmethod
    def must_say_delete(cls, value: str) -> str:
        if value.strip().upper() != "DELETE":
            raise ValueError("Type DELETE to confirm")
        return value


class SelfConfirmRequest(BaseModel):
    code: str = Field(min_length=6, max_length=10)


class CandidateEraseRequest(BaseModel):
    confirm: str = Field(min_length=1, max_length=50)
    reason: str | None = Field(default=None, max_length=1000)


class DownloadLink(BaseModel):
    url: str
    expires_in_seconds: int
