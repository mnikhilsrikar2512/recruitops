"""Legal documents and acceptances (Phase 5.1)."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

DocType = Literal["tos", "privacy", "dpa"]


class LegalDocumentResponse(BaseModel):
    doc_type: str
    version: int
    title: str
    body: str
    is_placeholder: bool
    effective_at: datetime


class LegalDocumentsResponse(BaseModel):
    items: list[LegalDocumentResponse]
    has_placeholders: bool


class LegalStatusItem(BaseModel):
    doc_type: str
    title: str
    current_version: int
    accepted_version: int | None = None
    accepted_at: datetime | None = None
    scope: Literal["user", "company"]
    needs_acceptance: bool
    can_accept: bool
    is_placeholder: bool


class LegalStatusResponse(BaseModel):
    items: list[LegalStatusItem]
    # what this user must do now (blocking the app until done)
    pending: list[str]
    # the company still owes the DPA but this user can't accept it
    company_pending: list[str]


class LegalAcceptanceCreate(BaseModel):
    doc_type: DocType
    version: int = Field(ge=1)


class LegalAcceptanceRecord(BaseModel):
    id: int
    doc_type: str
    version: int
    accepted_at: datetime
    on_behalf_of_company: bool
    user_id: int
    user_name: str | None = None
    user_email: str | None = None
