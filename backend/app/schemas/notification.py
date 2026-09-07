from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.pagination import PaginationMeta

NotificationStatus = Literal["unread", "read", "archived", "delivered"]
NotificationPriority = Literal["low", "normal", "high", "critical"]


class NotificationCreate(BaseModel):
    location_id: int | None = None
    user_id: int
    title: str
    message: str
    module_name: str | None = None
    entity_type: str | None = None
    entity_id: int | None = None
    priority: NotificationPriority = "normal"
    action_url: str | None = None
    event_type: str | None = None
    source_type: str | None = None
    source_id: int | None = None


class NotificationListFilters(BaseModel):
    status: NotificationStatus | None = None
    priority: NotificationPriority | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class NotificationMarkReadRequest(BaseModel):
    status: Literal["read"] = "read"


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    location_id: int | None
    user_id: int
    title: str
    message: str
    module_name: str
    entity_type: str
    entity_id: int
    priority: str
    status: str
    action_url: str | None
    read_at: datetime | None
    created_at: datetime
    updated_at: datetime
    event_type: str | None = None
    source_type: str | None = None
    source_id: int | None = None


class NotificationListResponse(BaseModel):
    items: list[NotificationResponse]
    meta: PaginationMeta
