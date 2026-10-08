"""Phase 4.11 / 4.12 — withdraw reasons (incl. after an approved offer) and
requisition holds that freeze candidates and pause the clock.

Runs against the configured database (skipped when unreachable)."""
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


def _move(client, admin, application_id, body):
    return client.patch(f"/api/v1/pipeline/applications/{application_id}/stage", json=body, headers=admin["headers"])


def _requisition_of(application_id):
    with _engine().connect() as connection:
        return connection.execute(text("SELECT requisition_id FROM dbo.candidate_applications WHERE id = :a"),
                                  {"a": application_id}).scalar_one()


@pytest.fixture()
def apps(client, admin):
    engine = _engine()
    _cleanup(engine, admin["tenant_id"])
    seeded = [_seed_application(engine, admin, stage="interview", suffix=f"wh{i}") for i in range(3)]
    yield seeded
    with engine.begin() as connection:
        ids = ", ".join(str(int(a)) for a in seeded)
        connection.execute(text(
            f"DELETE FROM dbo.approval_requests WHERE request_type = N'offer-approval' AND source_id IN ({ids})"))
        connection.execute(text(
            "DELETE h FROM dbo.requisition_holds h JOIN dbo.candidate_applications ca ON ca.requisition_id = h.requisition_id "
            f"WHERE ca.id IN ({ids})"))
    _cleanup(engine, admin["tenant_id"])


def test_withdraw_with_no_reason_given(client, admin, apps):
    application = apps[0]
    missing = _move(client, admin, application, {"to_stage": "withdrawn"})
    assert missing.status_code == 422, missing.text
    other_without_note = _move(client, admin, application, {"to_stage": "withdrawn", "withdrawal_reason": "other"})
    assert other_without_note.status_code == 422, other_without_note.text

    done = _move(client, admin, application, {"to_stage": "withdrawn", "withdrawal_reason": "no_reason_given"})
    assert done.status_code == 200, done.text
    detail = client.get(f"/api/v1/pipeline/applications/{application}", headers=admin["headers"]).json()
    assert detail["application_status"] == "withdrawn"
    assert detail["withdrawal_reason"] == "no_reason_given"

    report = client.get("/api/v1/reports/withdrawal-reasons", headers=admin["headers"])
    assert report.status_code == 200, report.text
    codes = {row["reason_code"]: row for row in report.json()["items"]}
    assert codes["no_reason_given"]["label"] == "No reason given"


def test_withdraw_after_approved_offer_closes_the_offer(client, admin, apps):
    application = apps[1]
    with _engine().begin() as connection:
        connection.execute(text("UPDATE dbo.candidate_applications SET offer_status = N'approved' WHERE id = :a"),
                           {"a": application})
        connection.execute(text(
            "INSERT INTO dbo.approval_requests (branch_id, request_type, source_type, source_id, requested_by_user_id, status) "
            "SELECT r.branch_id, N'offer-approval', N'offer', ca.id, :u, N'pending' FROM dbo.candidate_applications ca "
            "JOIN dbo.requisitions r ON r.id = ca.requisition_id WHERE ca.id = :a"), {"a": application, "u": admin["user_id"]})

    done = _move(client, admin, application, {"to_stage": "withdrawn", "withdrawal_reason": "counter_offer",
                                              "notes": "current employer matched"})
    assert done.status_code == 200, done.text
    with _engine().connect() as connection:
        offer_status = connection.execute(text("SELECT offer_status FROM dbo.candidate_applications WHERE id = :a"),
                                          {"a": application}).scalar_one()
        approval = connection.execute(text(
            "SELECT status FROM dbo.approval_requests WHERE request_type = N'offer-approval' AND source_id = :a"),
            {"a": application}).scalar_one()
        reason = connection.execute(text(
            "SELECT TOP (1) change_reason FROM dbo.candidate_stage_history WHERE candidate_application_id = :a ORDER BY id DESC"),
            {"a": application}).scalar_one()
    assert offer_status == "withdrawn"
    assert approval == "cancelled"
    assert reason == "Withdrew: Took a counter-offer — current employer matched"

    no_new_offer = client.post("/api/v1/offers/", json={
        "candidate_application_id": application, "offered_ctc": 1000, "offer_currency": "INR",
        "requested_by_user_id": admin["user_id"]}, headers=admin["headers"])
    assert no_new_offer.status_code == 409, no_new_offer.text


def test_hold_freezes_candidates_and_pauses_clock(client, admin, apps):
    application = apps[2]
    requisition = _requisition_of(application)
    before = client.get(f"/api/v1/requisitions/{requisition}", headers=admin["headers"]).json()

    held = client.post(f"/api/v1/requisitions/{requisition}/hold", json={
        "reason_code": "client_budget", "note": "Q4 budget not released"}, headers=admin["headers"])
    assert held.status_code == 200, held.text
    assert held.json()["status"] == "on-hold"
    assert held.json()["active_hold"]["reason_label"] == "Budget not released"
    again = client.post(f"/api/v1/requisitions/{requisition}/hold", json={"reason_code": "hiring_freeze"},
                        headers=admin["headers"])
    assert again.status_code == 409

    frozen = _move(client, admin, application, {"to_stage": "client-interview"})
    assert frozen.status_code == 409, frozen.text
    assert "on hold" in frozen.json()["detail"]
    no_offer = client.post("/api/v1/offers/", json={
        "candidate_application_id": application, "offered_ctc": 1000, "offer_currency": "INR",
        "requested_by_user_id": admin["user_id"]}, headers=admin["headers"])
    assert no_offer.status_code == 409, no_offer.text

    # Pretend the hold started 5 days ago, then resume: the clock pauses.
    with _engine().begin() as connection:
        connection.execute(text(
            "UPDATE dbo.requisition_holds SET held_at = DATEADD(DAY, -5, SYSUTCDATETIME()) "
            "WHERE requisition_id = :r AND resumed_at IS NULL"), {"r": requisition})
    resumed = client.post(f"/api/v1/requisitions/{requisition}/resume", json={"note": "budget approved"},
                          headers=admin["headers"])
    assert resumed.status_code == 200, resumed.text
    body = resumed.json()
    assert body["status"] == before["status"]
    assert body["hold_days_total"] == 5
    assert body["target_closure_date"][:10] > before["target_closure_date"][:10]

    holds = client.get(f"/api/v1/requisitions/{requisition}/holds", headers=admin["headers"]).json()
    assert holds[0]["hold_days"] == 5 and holds[0]["resume_note"] == "budget approved"

    moves_again = _move(client, admin, application, {"to_stage": "client-interview"})
    assert moves_again.status_code == 200, moves_again.text


def test_hold_still_allows_withdraw(client, admin, apps):
    application = apps[0]
    requisition = _requisition_of(application)
    held = client.patch(f"/api/v1/requisitions/{requisition}/status", json={
        "status": "on-hold", "reason": "client asked to pause"}, headers=admin["headers"])
    assert held.status_code == 200, held.text
    withdraw = _move(client, admin, application, {"to_stage": "withdrawn", "withdrawal_reason": "not_responding"})
    assert withdraw.status_code == 200, withdraw.text
    reopened = client.patch(f"/api/v1/requisitions/{requisition}/status", json={
        "status": "open", "reason": "back on"}, headers=admin["headers"])
    assert reopened.status_code == 200, reopened.text
    assert reopened.json()["status"] == "open"
