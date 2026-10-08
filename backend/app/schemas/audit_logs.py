"""Audit log viewer (Phase 5.4)."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.schemas.pagination import PaginationMeta


class AuditLogItem(BaseModel):
    id: int
    actor_user_id: int
    actor_name: str | None = None
    actor_email: str | None = None
    location_id: int | None = None
    location_name: str | None = None
    entity_type: str
    entity_id: int
    action_type: str
    created_at: datetime
    ip_address: str | None = None


class AuditLogDetail(AuditLogItem):
    user_agent: str | None = None
    old_values: Any = None
    new_values: Any = None


class AuditLogListResponse(BaseModel):
    items: list[AuditLogItem]
    meta: PaginationMeta


class AuditLogFacets(BaseModel):
    entity_types: list[str]
    action_types: list[str]
