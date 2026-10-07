"""Phase 4.7 on a real database: exact e-mail/phone flags for review; a
similar name in the same location is only suggested; the same name in
another city is not reported."""
from __future__ import annotations

import pytest
from sqlalchemy import text

from tests.test_metric_buckets_db import _engine, admin, client  # noqa: F401  (fixtures)

MARK = "DupTier"


def _cleanup(engine):
    with engine.begin() as connection:
        connection.execute(text(
            "DELETE FROM dbo.candidate_duplicate_checks WHERE candidate_id IN (SELECT id FROM dbo.candidates WHERE source = :s) "
            "OR matched_candidate_id IN (SELECT id FROM dbo.candidates WHERE source = :s)"), {"s": MARK})
        connection.execute(text(
            "DELETE FROM dbo.duplicate_review_cases WHERE candidate_id IN (SELECT id FROM dbo.candidates WHERE source = :s)"), {"s": MARK})
        connection.execute(text("DELETE FROM dbo.candidates WHERE source = :s"), {"s": MARK})


def _candidate(engine, admin, name, email=None, phone=None, location=None):
    with engine.begin() as connection:
        return int(connection.execute(text(
            "INSERT INTO dbo.candidates (full_name, email, phone, current_location, source, created_by_user_id) "
            "OUTPUT INSERTED.id VALUES (:n, :e, :p, :l, :s, :u)"),
            {"n": name, "e": email, "p": phone, "l": location, "s": MARK, "u": admin["user_id"]}).scalar_one())


@pytest.fixture()
def people(client, admin):
    engine = _engine()
    _cleanup(engine)
    ids = {
        "subject": _candidate(engine, admin, "Zorawar Quintanilla", "zq.dup@example.com", "+91 90000 11111", "Bengaluru"),
        "same_email": _candidate(engine, admin, "Z. Q.", "ZQ.Dup@Example.com", None, "Pune"),
        "same_phone": _candidate(engine, admin, "Someone Else", None, "9000011111", "Delhi"),
        "similar_here": _candidate(engine, admin, "Zorawar Quintanila", None, None, "bengaluru"),
        "same_name_elsewhere": _candidate(engine, admin, "Zorawar Quintanilla", None, None, "Chennai"),
        "lonely": _candidate(engine, admin, "Zorawar Quintanila", None, None, "Bengaluru"),
    }
    yield ids
    _cleanup(engine)


def test_exact_tier_flags_and_suggested_tier_hints(client, admin, people):
    response = client.get(f"/api/v1/candidates/{people['subject']}/duplicate-check", headers=admin["headers"])
    assert response.status_code == 200, response.text
    body = response.json()
    tiers = {m["matched_candidate_id"]: m["match_tier"] for m in body["matches"]}
    assert tiers.get(people["same_email"]) == "exact"
    assert tiers.get(people["same_phone"]) == "exact"
    assert tiers.get(people["similar_here"]) == "suggested"
    assert people["same_name_elsewhere"] not in tiers
    assert body["duplicate_state"] == "in-review"


def test_suggestions_alone_do_not_flag(client, admin, people):
    # "lonely" shares only a similar name + city with "similar_here"/"subject": hints, no flag.
    response = client.get(f"/api/v1/candidates/{people['lonely']}/duplicate-check", headers=admin["headers"])
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["matches"], "expected similar-name suggestions"
    assert all(m["match_tier"] == "suggested" for m in body["matches"])
    assert body["duplicate_state"] == "cleared"
