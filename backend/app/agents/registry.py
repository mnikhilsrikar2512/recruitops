"""V1 agent registry.

Each entry is declared from the PRD §4.16 "Named agents (V1)" table.
Every agent carries its own permission code (``ai.agent.<id>``) on top of
the base ``ai.use`` permission.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AgentDefinition:
    id: str
    name: str
    job: str
    where_used: str
    output: str
    required_permission: str
    allowed_tools: tuple[str, ...]


AGENT_DEFINITIONS: tuple[AgentDefinition, ...] = (
    AgentDefinition(
        id="resume_screener",
        name="Resume Screener",
        job="Parse resume from object storage; extract skills/experience; score vs a requisition when one is selected",
        where_used="Resume upload/review, candidate detail",
        output="Structured profile draft + match notes (user confirms before save)",
        required_permission="ai.agent.resume_screener",
        allowed_tools=("read_candidate", "read_candidate_resume", "read_requisition"),
    ),
    AgentDefinition(
        id="daily_brief",
        name="Daily Brief",
        job="Summarize a user's or team's daily updates / my-work queue",
        where_used="Role dashboard, daily review, manager review",
        output="Short brief + suggested focus items",
        required_permission="ai.agent.daily_brief",
        allowed_tools=("read_daily_updates", "read_workflow_queue"),
    ),
    AgentDefinition(
        id="inbox_triage",
        name="Inbox Triage",
        job="Prioritize notifications; rewrite unclear copy into What / Why / Next",
        where_used="Notifications center",
        output="Sorted queue + clearer headlines (apply on view; mark-read still user-driven)",
        required_permission="ai.agent.inbox_triage",
        allowed_tools=("read_notifications",),
    ),
)

AGENT_REGISTRY: dict[str, AgentDefinition] = {
    definition.id: definition for definition in AGENT_DEFINITIONS
}


def find_agent_by_id(agent_id: str) -> AgentDefinition | None:
    return AGENT_REGISTRY.get(agent_id)