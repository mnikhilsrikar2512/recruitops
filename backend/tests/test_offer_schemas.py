from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.offer import OfferCreate, OfferDecisionUpdate, OfferListFilters


def test_offer_create_normalizes_currency_and_notes() -> None:
    payload = OfferCreate(
        candidate_application_id=501,
        offered_ctc=Decimal("145000"),
        offer_currency=" usd ",
        offer_notes="  Send with relocation terms.  ",
    )

    assert payload.offer_currency == "USD"
    assert payload.offer_notes == "Send with relocation terms."


def test_offer_decision_normalizes_status() -> None:
    payload = OfferDecisionUpdate(status="Pending Approval", decision_notes="  Needs HR review.  ")

    assert payload.status == "pending-approval"
    assert payload.decision_notes == "Needs HR review."


def test_offer_filters_reject_unknown_status() -> None:
    with pytest.raises(ValidationError):
        OfferListFilters(status="waiting")
