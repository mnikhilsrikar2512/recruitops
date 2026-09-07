from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.pagination import PaginationMeta

WorkflowActionStatus = Literal["open", "in-progress", "resolved", "dismissed", "cancelled"]
WorkflowActionPriority = Literal["low", "normal", "high", "critical"]
WorkflowActionEventType = Literal[
    "view",
    "do_now",
    "review",
    "schedule",
    "nudge",
    "resolve",
    "dismiss",
    "submit_overlay",
]


def _normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


class WorkflowActionQueueFilters(BaseModel):
    status: WorkflowActionStatus | None = "open"
    source: str | None = Field(default=None, min_length=1, max_length=80)
    location_id: int | None = Field(default=None, ge=1)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    @field_validator("source")
    @classmethod
    def normalize_source(cls, value: str | None) -> str | None:
        return _normalize_text(value)


class WorkflowActionEventCreate(BaseModel):
    action_type: WorkflowActionEventType
    notes: str | None = Field(default=None, max_length=1000)
    payload: dict[str, Any] = Field(default_factory=dict)

    @field_validator("notes")
    @classmethod
    def normalize_notes(cls, value: str | None) -> str | None:
        return _normalize_text(value)


class WorkflowActionResolveRequest(BaseModel):
    resolution_notes: str | None = Field(default=None, max_length=1000)
    payload: dict[str, Any] = Field(default_factory=dict)

    @field_validator("resolution_notes")
    @classmethod
    def normalize_notes(cls, value: str | None) -> str | None:
        return _normalize_text(value)


class WorkflowActionNudgeRequest(BaseModel):
    target_user_id: int | None = Field(default=None, ge=1)
    message: str | None = Field(default=None, max_length=500)
    payload: dict[str, Any] = Field(default_factory=dict)

    @field_validator("message")
    @classmethod
    def normalize_message(cls, value: str | None) -> str | None:
        return _normalize_text(value)


class OverlaySubmissionCreate(BaseModel):
    overlay_key: str = Field(min_length=1, max_length=100)
    parent_route: str | None = Field(default=None, max_length=150)
    action_item_id: int | None = Field(default=None, ge=1)
    entity_type: str = Field(min_length=1, max_length=80)
    entity_id: int | None = Field(default=None, ge=1)
    action_type: str = Field(min_length=1, max_length=80)
    payload: dict[str, Any] = Field(default_factory=dict)
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator("overlay_key", "parent_route", "entity_type", "action_type", "notes")
    @classmethod
    def normalize_text_fields(cls, value: str | None) -> str | None:
        return _normalize_text(value)

    @model_validator(mode="after")
    def ensure_context_present(self) -> "OverlaySubmissionCreate":
        if self.action_item_id is None and self.entity_id is None:
            raise ValueError("Either action_item_id or entity_id must be provided")
        return self


class WorkflowActionItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    action_key: str
    source: str
    title: str
    description: str | None
    priority: str
    status: str
    location_id: int | None
    entity_type: str
    entity_id: int | None
    age_label: str | None
    primary_action_label: str
    secondary_action_label: str | None
    route_href: str | None
    overlay_key: str | None
    assigned_user_id: int | None
    assigned_role_code: str | None
    due_at: datetime | None
    resolved_at: datetime | None
    created_at: datetime
    updated_at: datetime


class WorkflowActionEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    action_item_id: int | None
    overlay_key: str | None
    actor_user_id: int
    action_type: str
    event_status: str
    notes: str | None
    payload: dict[str, Any]
    next_route_href: str | None
    created_at: datetime


class WorkflowActionQueueResponse(BaseModel):
    items: list[WorkflowActionItemResponse]
    meta: PaginationMeta
