"""Phase 4.11 (D-4.11): why a candidate withdrew, and why a requisition is
on hold (4.12). Short fixed lists so reports can group them; the free-text
note stays optional except for "other"."""
from __future__ import annotations

from typing import Literal

WithdrawalReason = Literal[
    "no_reason_given",
    "accepted_other_offer",
    "counter_offer",
    "compensation",
    "location_or_relocation",
    "role_or_work_mismatch",
    "notice_period",
    "personal_or_health",
    "not_responding",
    "other",
]

WITHDRAWAL_REASON_LABELS: dict[str, str] = {
    "no_reason_given": "No reason given",
    "accepted_other_offer": "Accepted another offer",
    "counter_offer": "Took a counter-offer",
    "compensation": "Compensation",
    "location_or_relocation": "Location / relocation",
    "role_or_work_mismatch": "Role or work-mode mismatch",
    "notice_period": "Notice period",
    "personal_or_health": "Personal / health",
    "not_responding": "Stopped responding",
    "other": "Other",
}

HoldReason = Literal[
    "client_budget",
    "hiring_freeze",
    "role_being_redefined",
    "client_reorganisation",
    "internal_candidate",
    "awaiting_client_approval",
    "client_unresponsive",
    "other",
]

HOLD_REASON_LABELS: dict[str, str] = {
    "client_budget": "Budget not released",
    "hiring_freeze": "Hiring freeze",
    "role_being_redefined": "Role being redefined",
    "client_reorganisation": "Reorganisation",
    "internal_candidate": "Considering an internal candidate",
    "awaiting_client_approval": "Awaiting approval",
    "client_unresponsive": "Client not responding",
    "other": "Other",
}

# Offer states that a withdrawal closes out (the candidate won't take it).
OPEN_OFFER_STATUSES = ("draft", "pending-approval", "approved", "sent", "accepted")
