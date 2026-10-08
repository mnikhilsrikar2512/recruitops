"""Python twin of the SQL stage resolver (scripts/016_metric_buckets.sql).

The database (dbo.fn_metric_bucket) is the source of truth: it also knows
the company's own mappings and template stages. This twin holds only the
platform defaults and the name heuristic, for code paths that run without
a database (unit tests) — tests/test_stage_buckets_twin.py fails the build
if it drifts from the SQL seed.
"""
from __future__ import annotations

BUCKET_ORDER: dict[str, int] = {
    "sourced": 10, "screened": 20, "submitted": 30, "interview": 40,
    "offer": 50, "joined": 60, "rejected": 70, "withdrawn": 80,
}
TERMINAL_BUCKETS = frozenset({"joined", "rejected", "withdrawn"})
BUCKET_LABELS = {
    "sourced": "Sourced", "screened": "Screened", "submitted": "Submitted", "interview": "Interview",
    "offer": "Offer", "joined": "Joined", "rejected": "Rejected", "withdrawn": "Withdrawn",
}

PLATFORM_STAGE_BUCKETS: dict[str, str] = {
    "sourced": "sourced", "new": "sourced", "applied": "sourced", "identified": "sourced",
    "screening": "screened", "screened": "screened", "internal-screening": "screened",
    "shortlisted": "screened", "recruiter-screen": "screened",
    "submitted": "submitted", "submitted-to-client": "submitted", "client-review": "submitted",
    "interview": "interview", "technical-interview": "interview", "executive-review": "interview",
    "client-interview": "interview",
    "offer": "offer", "offered": "offer", "offer-accepted": "offer",
    "joined": "joined", "hired": "joined",
    "rejected": "rejected", "client-rejected": "rejected",
    "withdrawn": "withdrawn",
}


def stage_key(label: str) -> str:
    """Twin of dbo.fn_stage_key: lower-case, '-' for spaces and '_'."""
    return (label or "").strip().replace("_", "-").replace(" ", "-").lower()


def bucket_for_label(label: str | None) -> str | None:
    if label is None:
        return None
    key = stage_key(label)
    if key in PLATFORM_STAGE_BUCKETS:
        return PLATFORM_STAGE_BUCKETS[key]

    def has(*parts: str) -> bool:
        return any(part in key for part in parts)

    if has("withdr", "pulled-out"):
        return "withdrawn"
    if has("reject", "declin", "no-fit"):
        return "rejected"
    if has("join", "hired", "onboard", "placed"):
        return "joined"
    if has("offer"):
        return "offer"
    if has("interview", "review", "panel", "assessment"):
        return "interview"
    if has("submit"):
        return "submitted"
    if has("screen", "shortlist"):
        return "screened"
    if has("sourc"):
        return "sourced"
    return "interview"
