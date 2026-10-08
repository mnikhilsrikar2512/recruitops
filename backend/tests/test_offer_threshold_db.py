"""Phase 4 exit gate — an offer below the company threshold is approved
directly; above it creates an approval; the default threshold 0 sends every
paid offer to approval (D-06, scripts/020_offer_threshold.sql)."""
from __future__ import annotations

import pytest
from sqlalchemy import text

from tests.test_metric_buckets_db import (  # noqa: F401  (fixtures)
    _cleanup,
    _engine,
    _seed_application,
    admin,
    client,
)


@pytest.fixture()
def offer_setup(client, admin):
    engine = _engine()
    _cleanup(engine, admin["tenant_id"])
    with engine.connect() as connection:
        before, bonus_before, counts_before = connection.execute(text(
            "SELECT offer_approval_threshold, offers_signing_bonus, bonus_counts_against_budget FROM dbo.tenants WHERE id = :t"),
            {"t": admin["tenant_id"]}).one()
    with engine.begin() as connection:
        connection.execute(text("UPDATE dbo.tenants SET offers_signing_bonus = 1, bonus_counts_against_budget = 1 WHERE id = :t"),
                           {"t": admin["tenant_id"]})
    apps = [_seed_application(engine, admin, stage="interview", suffix=f"offer{i}") for i in range(8)]
    with engine.begin() as connection:
        branch_ids = connection.execute(text(
            "SELECT DISTINCT r.branch_id FROM dbo.candidate_applications ca JOIN dbo.requisitions r ON r.id = ca.requisition_id "
            f"WHERE ca.id IN ({', '.join(str(int(a)) for a in apps)})")).scalars().all()
        toggles = {b: connection.execute(text("SELECT offers_enabled FROM dbo.branches WHERE id = :b"), {"b": b}).scalar()
                   for b in branch_ids}
        for b in branch_ids:
            connection.execute(text("UPDATE dbo.branches SET offers_enabled = 1 WHERE id = :b"), {"b": b})
    yield apps
    with engine.begin() as connection:
        for b, value in toggles.items():
            connection.execute(text("UPDATE dbo.branches SET offers_enabled = :v WHERE id = :b"), {"b": b, "v": value})
        connection.execute(text(
            "UPDATE dbo.tenants SET offer_approval_threshold = :v, offers_signing_bonus = :b, "
            "bonus_counts_against_budget = :c WHERE id = :t"),
            {"v": before, "b": bonus_before, "c": counts_before, "t": admin["tenant_id"]})
        connection.execute(text(
            "DELETE FROM dbo.approval_requests WHERE request_type = N'offer-approval' "
            f"AND source_id IN ({', '.join(str(int(a)) for a in apps)})"))
    _cleanup(engine, admin["tenant_id"])


def _offer(client, admin, application_id, ctc, bonus=None):
    response = client.post("/api/v1/offers/", json={
        "candidate_application_id": application_id, "offered_ctc": ctc, "signing_bonus": bonus,
        "offer_currency": "INR", "requested_by_user_id": admin["user_id"],
    }, headers=admin["headers"])
    assert response.status_code == 201, response.text
    return response.json()


def _approvals(application_id):
    with _engine().connect() as connection:
        return connection.execute(text(
            "SELECT COUNT(*) FROM dbo.approval_requests WHERE request_type = N'offer-approval' AND source_id = :a"
        ), {"a": application_id}).scalar_one()


def test_threshold_routes_offers(client, admin, offer_setup):
    below, above, default = offer_setup[:3]

    assert client.get("/api/v1/settings/offer-approval", headers=admin["headers"]).status_code == 200
    set_response = client.put("/api/v1/settings/offer-approval", json={"threshold": 500000}, headers=admin["headers"])
    assert set_response.status_code == 200, set_response.text
    assert set_response.json()["threshold"] == 500000

    direct = _offer(client, admin, below, 400000, 100000)  # total == threshold -> direct
    assert direct["offer_status"] == "approved"
    assert _approvals(below) == 0

    routed = _offer(client, admin, above, 450000, 60000)  # total above -> approval
    assert routed["offer_status"] == "pending-approval"
    assert _approvals(above) == 1

    assert client.put("/api/v1/settings/offer-approval", json={"threshold": 0}, headers=admin["headers"]).status_code == 200
    everything = _offer(client, admin, default, 1000)
    assert everything["offer_status"] == "pending-approval"
    assert _approvals(default) == 1


def test_negative_threshold_rejected(client, admin):
    response = client.put("/api/v1/settings/offer-approval", json={"threshold": -1}, headers=admin["headers"])
    assert response.status_code == 422


def test_requisition_budget_decides_when_set(client, admin, offer_setup):
    """A requisition with a max budget overrides the company threshold."""
    within, over = offer_setup[3:5]
    with _engine().begin() as connection:
        connection.execute(text(
            "UPDATE r SET budget_max = 800000, currency_code = N'INR', version = r.version + 1 "
            "FROM dbo.requisitions r JOIN dbo.candidate_applications ca ON ca.requisition_id = r.id "
            f"WHERE ca.id IN ({int(within)}, {int(over)})"))
    # Company threshold 0 would send everything to approval; the budget wins.
    assert client.put("/api/v1/settings/offer-approval", json={"threshold": 0}, headers=admin["headers"]).status_code == 200

    inside = _offer(client, admin, within, 700000, 100000)  # total == budget -> direct
    assert inside["offer_status"] == "approved"
    assert _approvals(within) == 0

    outside = _offer(client, admin, over, 800000, 1)  # just over budget -> approval
    assert outside["offer_status"] == "pending-approval"
    assert _approvals(over) == 1


def _client_of(application_id):
    with _engine().connect() as connection:
        return connection.execute(text(
            "SELECT r.client_company_id FROM dbo.candidate_applications ca JOIN dbo.requisitions r ON r.id = ca.requisition_id "
            "WHERE ca.id = :a"), {"a": application_id}).scalar_one()


def test_signing_bonus_switches(client, admin, offer_setup):
    """Phase 4.13: company switches, client overrides, CTC-only comparison."""
    no_bonus, ctc_only, client_override = offer_setup[5:8]
    with _engine().begin() as connection:
        connection.execute(text(
            "UPDATE r SET budget_max = 1000000, currency_code = N'INR', version = r.version + 1 "
            "FROM dbo.requisitions r JOIN dbo.candidate_applications ca ON ca.requisition_id = r.id "
            f"WHERE ca.id IN ({int(no_bonus)}, {int(ctc_only)}, {int(client_override)})"))

    # Company stops paying bonuses: the form is told, and a bonus is refused.
    response = client.put("/api/v1/settings/offer-approval",
                          json={"threshold": 0, "offers_signing_bonus": False}, headers=admin["headers"])
    assert response.status_code == 200, response.text
    assert response.json()["offers_signing_bonus"] is False
    policy = client.get(f"/api/v1/offers/policy/{no_bonus}", headers=admin["headers"]).json()
    assert policy["signing_bonus_allowed"] is False and policy["source"] == "client"
    refused = client.post("/api/v1/offers/", json={
        "candidate_application_id": no_bonus, "offered_ctc": 900000, "signing_bonus": 50000,
        "offer_currency": "INR", "requested_by_user_id": admin["user_id"]}, headers=admin["headers"])
    assert refused.status_code == 422, refused.text
    assert _offer(client, admin, no_bonus, 900000)["offer_status"] == "approved"

    # This client pays a bonus but it doesn't count against the budget.
    override = client.patch(f"/api/v1/clients/{_client_of(client_override)}", json={
        "offers_signing_bonus": True, "bonus_counts_against_budget": False}, headers=admin["headers"])
    assert override.status_code == 200, override.text
    assert override.json()["offers_signing_bonus"] is True
    assert _offer(client, admin, client_override, 950000, 200000)["offer_status"] == "approved"

    # Company turns bonuses back on and counts them: the same split needs approval.
    assert client.put("/api/v1/settings/offer-approval", json={
        "threshold": 0, "offers_signing_bonus": True, "bonus_counts_against_budget": True},
        headers=admin["headers"]).status_code == 200
    assert _offer(client, admin, ctc_only, 950000, 200000)["offer_status"] == "pending-approval"
