from datetime import datetime
from typing import Optional, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.pagination import PaginationMeta

NotificationStatus = Literal["unread", "read", "archived", "delivered"]
NotificationPriority = Literal["low", "normal", "high", "critical"]


class NotificationCreate(BaseModel):
    location_id: Optional[int] = None
    user_id: int
    title: str = ""
    message: str
    module_name: Optional[str] = None
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    priority: NotificationPriority = "normal"
    action_url: Optional[str] = None
    event_type: Optional[str] = None
    source_type: Optional[str] = None
    source_id: Optional[int] = None


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    location_id: Optional[int] = None
    user_id: int
    title: str
    message: str
    module_name: Optional[str] = None
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    priority: str
    status: str
    action_url: Optional[str] = None
    read_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    event_type: Optional[str] = None
    source_type: Optional[str] = None
    source_id: Optional[int] = None


class NotificationListFilters(BaseModel):
    status: Optional[NotificationStatus] = None
    priority: Optional[NotificationPriority] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class NotificationMarkReadRequest(BaseModel):
    status: Literal["read"] = "read"


class NotificationListResponse(BaseModel):
    items: list[NotificationResponse]
    meta: PaginationMeta
