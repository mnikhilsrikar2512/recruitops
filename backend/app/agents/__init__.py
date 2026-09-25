"""AI orchestration for RecruitOps V1 agents.

Agents propose; humans confirm. Every run is persisted to ``agent_runs``
and written to the audit log. The LLM provider is pluggable via
``settings.ai_provider`` (V1 ships an offline deterministic ``mock``
provider so the feature runs and tests without API keys).
"""

from app.agents.registry import AGENT_DEFINITIONS, AGENT_REGISTRY, find_agent_by_id
from app.agents.runner import decide_agent_run, run_agent

__all__ = [
    "AGENT_DEFINITIONS",
    "AGENT_REGISTRY",
    "find_agent_by_id",
    "run_agent",
    "decide_agent_run",
]