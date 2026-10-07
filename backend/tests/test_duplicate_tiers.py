"""Phase 4.7 unit tests: duplicate tiers and cross-company redaction."""
from unittest.mock import MagicMock

from app.repositories import candidates as repo


def _engine_returning(exact_rows, fuzzy_rows):
    engine = MagicMock()
    connection = engine.connect.return_value.__enter__.return_value
    results = iter([exact_rows, fuzzy_rows])
    connection.execute.side_effect = lambda *a, **k: MagicMock(mappings=lambda: MagicMock(all=lambda: next(results)))
    return engine


def _row(**values):
    base = {
        "matched_candidate_id": 2, "matched_candidate_name": "Priya Raghavan", "email": "p@example.com",
        "phone": "+91 98765 43210", "current_company": "Acme", "current_designation": "Engineer",
        "duplicate_state": "cleared",
    }
    base.update(values)
    return base


def test_name_similarity_ignores_order_case_and_punctuation():
    assert repo._name_similarity("Raghavan, Priya", "priya raghavan") == 1.0
    assert repo._name_similarity("Priya Ragavan", "Priya Raghavan") >= 0.85
    assert repo._name_similarity("Priya Raghavan", "Rahul Sharma") < 0.85
    assert repo._phone_digits("+91 (987) 654-3210") == "9876543210"


def test_exact_match_in_another_company_hides_contact_details():
    engine = _engine_returning([_row(email_match=0, phone_match=1, in_tenant=0)], [])
    [match] = repo.find_duplicate_matches(engine, 1, tenant_id=7)
    assert match.match_tier == "exact" and match.match_reasons == ["phone_match"]
    assert match.in_your_company is False
    assert (match.email, match.phone, match.current_company) == (None, None, None)


def test_suggested_tier_needs_similar_name_and_is_capped_below_exact():
    engine = _engine_returning(
        [],
        [_row(matched_candidate_id=3, matched_candidate_name="Priya Ragavan", current_name="Priya Raghavan"),
         _row(matched_candidate_id=4, matched_candidate_name="Pranav Rao", current_name="Priya Raghavan")],
    )
    matches = repo.find_duplicate_matches(engine, 1, tenant_id=7)
    assert [m.matched_candidate_id for m in matches] == [3]
    assert matches[0].match_tier == "suggested" and matches[0].match_score < 80
