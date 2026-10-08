"""Phase 4.6 — terminal-state guard, backward moves need a reason, reopen.

Runs against the configured database (skipped when unreachable). Uses
company-custom stage labels on purpose: the guards read metric buckets, so
"Candidate Pulled Out" is treated exactly like "withdrawn".
"""
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


def _reopen(client, admin, application_id, body):
    return client.post(f"/api/v1/pipeline/applications/{application_id}/reopen", json=body, headers=admin["headers"])


@pytest.fixture()
def application(client, admin):
    engine = _engine()
    _cleanup(engine, admin["tenant_id"])
    application_id = _seed_application(engine, admin, stage="Technical Interview", suffix="lifecycle")
    yield application_id
    _cleanup(engine, admin["tenant_id"])


def test_backward_move_needs_a_reason(client, admin, application):
    blocked = _move(client, admin, application, {"to_stage": "shortlisted"})
    assert blocked.status_code == 409, blocked.text
    assert "needs a reason" in blocked.json()["detail"]

    allowed = _move(client, admin, application, {"to_stage": "shortlisted", "notes": "client asked for a re-screen"})
    assert allowed.status_code == 200, allowed.text


def test_withdrawn_is_terminal_until_reopened(client, admin, application):
    no_reason = _move(client, admin, application, {"to_stage": "Candidate Pulled Out"})
    assert no_reason.status_code == 422, no_reason.text

    withdrawn = _move(client, admin, application, {"to_stage": "Candidate Pulled Out", "notes": "accepted another offer"})
    assert withdrawn.status_code == 200, withdrawn.text
    assert withdrawn.json()["application_status"] == "withdrawn"

    stuck = _move(client, admin, application, {"to_stage": "interview", "notes": "try again"})
    assert stuck.status_code == 409
    assert "closed (Withdrawn)" in stuck.json()["detail"]

    into_terminal = _reopen(client, admin, application, {"to_stage": "rejected", "reason": "wrong target"})
    assert into_terminal.status_code == 422

    reopened = _reopen(client, admin, application, {"to_stage": "interview", "reason": "candidate came back"})
    assert reopened.status_code == 200, reopened.text
    assert reopened.json()["application_status"] == "active"
    assert reopened.json()["to_stage"] == "interview"

    again = _reopen(client, admin, application, {"to_stage": "interview", "reason": "twice"})
    assert again.status_code == 409

    with _engine().connect() as connection:
        history = connection.execute(text(
            "SELECT to_stage, to_bucket, source_type, change_reason FROM dbo.candidate_stage_history "
            "WHERE candidate_application_id = :a ORDER BY id"
        ), {"a": application}).mappings().all()
        audited = connection.execute(text(
            "SELECT COUNT(*) FROM dbo.audit_logs WHERE entity_type = N'candidate_application' "
            "AND entity_id = :a AND action_type = N'pipeline.reopen'"
        ), {"a": application}).scalar_one()
    assert [(h["to_bucket"], h["source_type"]) for h in history] == [("withdrawn", "manual"), ("interview", "reopen")]
    assert history[-1]["change_reason"] == "candidate came back"
    assert audited == 1


def test_reopen_needs_a_reason(client, admin, application):
    response = _reopen(client, admin, application, {"to_stage": "interview", "reason": ""})
    assert response.status_code == 422
