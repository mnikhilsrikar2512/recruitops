from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.pagination import PaginationMeta

AgentRunStatus = Literal["pending", "accepted", "rejected", "failed"]
AgentDecision = Literal["accept", "reject"]


class AgentInfo(BaseModel):
    id: str
    name: str
    job: str
    where_used: str
    output: str
    required_permission: str


class AgentCatalogResponse(BaseModel):
    items: list[AgentInfo]


class AgentRunRequest(BaseModel):
    candidate_id: Optional[int] = Field(default=None, ge=1)
    requisition_id: Optional[int] = Field(default=None, ge=1)
    resume_document_id: Optional[int] = Field(default=None, ge=1)
    scope: Literal["me", "team", "location"] = "me"
    status: Optional[str] = None
    max_items: int = Field(default=20, ge=1, le=100)


class AgentRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    agent_id: str
    status: str
    input_refs: dict[str, Any]
    output_draft: dict[str, Any]
    output_summary: str
    actor_user_id: int
    location_id: Optional[int] = None
    decided_by_user_id: Optional[int] = None
    decided_at: Optional[datetime] = None
    decision_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class AgentRunListResponse(BaseModel):
    items: list[AgentRunResponse]
    meta: PaginationMeta


class AgentRunDecisionRequest(BaseModel):
    decision: AgentDecision
    decision_notes: Optional[str] = Field(default=None, max_length=1000)