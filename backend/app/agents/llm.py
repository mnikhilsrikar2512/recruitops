"""Pluggable LLM provider boundary for V1 agents.

The runner never talks to a model directly; it calls an ``LLMProvider``
that turns an input context (read-only tool output) into a structured
parseable final result::

    {"output_draft": {...}, "output_summary": "string"}

V1 ships the deterministic ``MockLLMProvider`` so the feature works
offline and is fully testable. Production can plug in an OpenAI-compatible
provider by adding a new factory branch in :func:`get_llm_provider`.
"""
from __future__ import annotations

from typing import Protocol, TypedDict

from app.agents.registry import AgentDefinition
from app.core.config import settings


class LLMResult(TypedDict):
    output_draft: dict
    output_summary: str


class LLMProvider(Protocol):
    def generate(self, agent_id: str, input_context: dict, spec: AgentDefinition) -> LLMResult:
        """Return a structured draft + one-line summary for an agent run."""
        ...


def _iso(value) -> str:
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


class MockLLMProvider:
    """Deterministic offline provider.

    Produces agent-shaped output derived from the read-only input context
    so the whole loop (tools -> draft -> audit -> accept/reject) is
    testable end to end without network access.
    """

    def generate(self, agent_id: str, input_context: dict, spec: AgentDefinition) -> LLMResult:
        generators = {
            "resume_screener": self._resume_draft,
            "daily_brief": self._daily_brief,
            "inbox_triage": self._inbox_triage,
        }
        generator = generators.get(agent_id)
        if generator is None:
            raise NotImplementedError(f"Agent '{agent_id}' has no mock generator")
        return generator(input_context)

    @staticmethod
    def _resume_draft(context: dict) -> LLMResult:
        candidate = context.get("candidate") or {}
        requisition = context.get("requisition")
        full_name = candidate.get("full_name") or "Candidate"
        designations = [candidate.get("current_designation") or ""]
        haystack = " ".join(designations + [candidate.get("current_company") or ""]).lower()

        must_have = (requisition or {}).get("must_have_skills") or []
        good_to_have = (requisition or {}).get("good_to_have_skills") or []
        extracted = [skill for skill in must_have + good_to_have if skill.lower() in haystack]
        match_score = round(len(extracted) / len(must_have), 2) if must_have else None

        profile = {
            "full_name": full_name,
            "current_designation": candidate.get("current_designation"),
            "current_company": candidate.get("current_company"),
            "total_experience_years": candidate.get("total_experience_years"),
            "source_type": candidate.get("source_type"),
            "resume": candidate.get("resume"),
        }
        draft = {
            "profile": profile,
            "extracted_skills": extracted,
            "match_score": match_score,
            "match_notes": [
                f"Matched {len(extracted)} of {len(must_have)} must-have skills"
                if must_have
                else "No requisition selected; skills listed for manual review",
            ],
        }
        req_label = (requisition or {}).get("title") or "no requisition"
        summary = (
            f"Extracted {len(extracted)} skills from {full_name}'s profile; "
            f"match {match_score * 100:.0f}% vs {req_label}."
            if match_score is not None
            else f"Extracted {len(extracted)} skills from {full_name}'s profile."
        )
        return {"output_draft": draft, "output_summary": summary}

    @staticmethod
    def _daily_brief(context: dict) -> LLMResult:
        updates = context.get("updates") or []
        actions = context.get("actions") or []
        stats = {
            "profiles_sourced": sum(u.get("profiles_sourced_count") or 0 for u in updates),
            "profiles_screened": sum(u.get("profiles_screened_count") or 0 for u in updates),
            "profiles_submitted": sum(u.get("profiles_submitted_count") or 0 for u in updates),
            "interviews_scheduled": sum(u.get("interviews_scheduled_count") or 0 for u in updates),
            "offers_closed": sum(u.get("offers_closed_count") or 0 for u in updates),
        }
        blockers = [u.get("blockers") for u in updates if u.get("blockers")]
        focus_items = [
            {"title": a.get("title"), "priority": a.get("priority"), "entity_type": a.get("entity_type")}
            for a in actions
        ]
        draft = {"context": context.get("scope"), "stats": stats, "blockers": blockers[:3], "focus_items": focus_items}
        summary = (
            f"{len(updates)} updates over {context.get('scope')}: "
            f"{stats['profiles_screened']} screened, {len(focus_items)} focus items."
        )
        return {"output_draft": draft, "output_summary": summary}

    @staticmethod
    def _inbox_triage(context: dict) -> LLMResult:
        notifications = context.get("notifications") or []
        priority_order = {"critical": 0, "high": 1, "normal": 2, "low": 3}
        sorted_items = sorted(
            notifications,
            key=lambda item: priority_order.get(item.get("priority", "normal"), 4),
        )
        queue = [
            {
                "id": item.get("id"),
                "module": item.get("module_name"),
                "what": item.get("title") or item.get("message")[:80],
                "why": item.get("message"),
                "next": f"Open {item.get('entity_type', 'item')} and review",
                "priority": item.get("priority"),
            }
            for item in sorted_items
        ]
        draft = {"summary": f"{len(queue)} notifications prioritized for review.", "queue": queue}
        return {"output_draft": draft, "output_summary": draft["summary"]}


def get_llm_provider(provider_name: str | None = None) -> LLMProvider:
    provider = (provider_name or settings.ai_provider or "mock").lower()
    if provider == "mock":
        return MockLLMProvider()
    raise NotImplementedError(
        f"AI provider '{provider}' is not registered. Set AI_PROVIDER=mock for the offline provider."
    )