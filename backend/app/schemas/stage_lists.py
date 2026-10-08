"""Client stage lists (Phase 4.10, D-4.10)."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

MetricBucket = Literal["sourced", "screened", "submitted", "interview", "offer", "joined", "rejected", "withdrawn"]


class StageItem(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    bucket: MetricBucket
    allows_rejection: bool = True

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        value = " ".join(value.split())
        if not value:
            raise ValueError("Stage name is required")
        return value


class StageListUpdate(BaseModel):
    stages: list[StageItem] = Field(min_length=2, max_length=25)
    # old stage label -> new stage name, for candidates in a dropped stage
    remap: dict[str, str] = Field(default_factory=dict)


class StageResponse(BaseModel):
    code: str
    name: str
    order: int
    bucket: str | None = None
    allows_rejection: bool = True
    is_terminal: bool = False


class StageListResponse(BaseModel):
    template_id: int | None = None
    source: str  # "client" | "company" | "platform"
    client_company_id: int | None = None
    client_name: str | None = None
    stages: list[StageResponse]


class ClientStageListSummary(BaseModel):
    client_id: int
    client_name: str
    template_id: int | None = None
    has_own_list: bool
    stage_count: int


class StageListOverview(BaseModel):
    company: StageListResponse
    clients: list[ClientStageListSummary]
