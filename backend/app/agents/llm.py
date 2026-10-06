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

import re

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
        haystack = " ".join(
            part
            for part in [
                candidate.get("current_designation") or "",
                candidate.get("current_company") or "",
            ]
            if part
        ).lower()

        must_have = (requisition or {}).get("must_have_skills") or []
        good_to_have = (requisition or {}).get("good_to_have_skills") or []

        def _matches(skill) -> bool:
            """Whole-word match, so "java" never matches "javascript".

            Lookarounds instead of \b keep symbol skills like c++ working
            (a trailing \b would demand a word char after '+').
            """
            if not skill:
                return False
            needle = str(skill).strip()
            if not needle:
                return False
            pattern = r"(?<!\w)" + re.escape(needle) + r"(?!\w)"
            return re.search(pattern, haystack, flags=re.IGNORECASE) is not None

        # Dedup and drop blanks on both sides of the ratio so repeated or
        # empty rows can't inflate or deflate the score; capped at 1.0
        # because matched good-to-have skills must never push a must-have
        # ratio over 100%.
        cleaned_must = [s for s in dict.fromkeys(must_have) if s and str(s).strip()]
        cleaned_good = [s for s in dict.fromkeys(good_to_have) if s and str(s).strip()]
        matched_must = [s for s in cleaned_must if _matches(s)]
        matched_good = [s for s in cleaned_good if _matches(s) and s not in matched_must]
        extracted = matched_must + matched_good
        match_score = min(round(len(matched_must) / len(cleaned_must), 2), 1.0) if cleaned_must else None

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
                f"Matched {len(matched_must)} of {len(cleaned_must)} must-have skills"
                + (f" (+{len(matched_good)} good-to-have)" if matched_good else "")
                if cleaned_must
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
        # Secondary sort key keeps the order deterministic for equal
        # priorities instead of depending on input ordering.
        sorted_items = sorted(
            notifications,
            key=lambda item: (
                priority_order.get(item.get("priority", "normal"), 4),
                -(item.get("id") or 0),
            ),
        )
        queue = []
        for item in sorted_items:
            message = item.get("message") or ""
            title = item.get("title") or message[:80] or "(untitled notification)"
            queue.append(
                {
                    "id": item.get("id"),
                    "module": item.get("module_name"),
                    "what": title,
                    "why": message,
                    "next": f"Open {item.get('entity_type') or 'item'} and review",
                    "priority": item.get("priority") or "normal",
                }
            )
        draft = {"summary": f"{len(queue)} notifications prioritized for review.", "queue": queue}
        return {"output_draft": draft, "output_summary": draft["summary"]}


def get_llm_provider(provider_name: str | None = None) -> LLMProvider:
    provider = (provider_name or settings.ai_provider or "mock").lower()
    if provider == "mock":
        return MockLLMProvider()
    raise NotImplementedError(
        f"AI provider '{provider}' is not registered. Set AI_PROVIDER=mock for the offline provider."
    )