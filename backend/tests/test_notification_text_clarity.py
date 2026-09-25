"""Focused tests that the notifications shipped by our services carry clear,
specific, actionable text (entity names + next step), not terse placeholders.

Each test drives a service function down to the notification boundary and
captures the ``NotificationCreate`` payload that would be stored.
"""
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

from tests.stubs import make_user_record

import app.services.pipeline as pipeline_mod
import app.services.candidates as candidates_mod
import app.services.requisitions as requisitions_mod
import app.services.daily_updates as daily_updates_mod
import app.services.workflow_actions as workflow_actions_mod
from app.schemas.candidate import (
    CandidateCreate,
    CandidateDuplicateDecisionPayload,
    CandidateFinalizePayload,
    CandidateOwnerReassignment,
)
from app.schemas.requisition import (
    RequisitionAssignmentCreate,
    RequisitionOwnerReassignment,
)
from app.schemas.workflow_action import WorkflowActionNudgeRequest
from app.services.auth import AuthContext


class _Capture:
    def __init__(self) -> None:
        self.payload = None

    def __call__(self, engine, payload):
        self.payload = payload
        return payload


class _Passthrough:
    @classmethod
    def model_validate(cls, obj, *args, **kwargs):
        return obj


def _auth_context(role_code: str = "admin", location_id: int = 4) -> AuthContext:
    user = SimpleNamespace(id=1, role_code=role_code, location_id=location_id)
    return AuthContext(session_id=1, session_token_hash="token", user=user)


def _candidate_payload() -> CandidateCreate:
    return CandidateCreate(
        full_name="Asha Verma",
        email="asha@example.com",
        phone="9999999999",
        source_type="linkedin",
        source_detail="direct search",
        current_company="Acme",
        current_designation="Engineer",
        primary_owner_user_id=22,
        sourced_by_user_id=21,
        created_by_user_id=20,
    )


def _assert_clear(payload, *, entity, keyword, action_url_host):
    assert payload is not None
    assert payload.title, "expected a short headline title"
    assert payload.title != payload.message, "title must be a distinct headline, not the full message"
    assert entity.lower() in payload.message.lower(), f"message should name the entity, got: {payload.message!r}"
    assert keyword.lower() in payload.message.lower(), f"message should tell you what to do next, got: {payload.message!r}"
    assert payload.action_url is not None
    assert action_url_host in payload.action_url


# --- pipeline ---------------------------------------------------------------

def test_pipeline_stage_changed_notification_is_specific(monkeypatch) -> None:
    capture = _Capture()
    monkeypatch.setattr(pipeline_mod, "create_notification_service", capture)
    monkeypatch.setattr(
        pipeline_mod,
        "find_pipeline_application_by_id",
        lambda engine, aid: SimpleNamespace(
            candidate_name="Ananya Rao",
            requisition_title="Senior Java Developer",
            current_stage="shortlisted",
            application_status="active",
            location_id=4,
        ),
    )
    monkeypatch.setattr(pipeline_mod, "find_pipeline_template_stage_for_application", lambda *a: None)
    monkeypatch.setattr(pipeline_mod, "application_has_pipeline_template", lambda *a: False)
    monkeypatch.setattr(
        pipeline_mod,
        "move_pipeline_stage",
        lambda engine, aid, payload: (
            "shortlisted",
            SimpleNamespace(
                location_id=4,
                owner_user_id=22,
                current_stage="interview",
                application_status="active",
                stage_updated_at=datetime(2026, 9, 1),
            ),
        ),
    )
    payload = SimpleNamespace(
        to_stage="interview",
        changed_by_user_id=None,
        changed_by_location_id=4,
        rejection_reason=None,
        joining_date=None,
    )

    pipeline_mod.move_pipeline_stage_service(MagicMock(), 101, payload)

    notif = capture.payload
    assert notif is not None
    assert notif.event_type == "pipeline_stage_changed"
    assert notif.user_id == 22
    _assert_clear(
        notif,
        entity="Ananya Rao",
        keyword="pipeline board",
        action_url_host="/pipeline/applications/101",
    )
    assert "Senior Java Developer" in notif.message


# --- candidates ------------------------------------------------------------

def test_candidate_assigned_notification_is_specific(monkeypatch) -> None:
    capture = _Capture()
    monkeypatch.setattr(candidates_mod, "create_notification_service", capture)
    monkeypatch.setattr(
        candidates_mod,
        "find_user_by_id",
        lambda engine, uid: make_user_record(user_id=uid, primary_location_id=4),
    )
    monkeypatch.setattr(
        candidates_mod,
        "create_candidate",
        lambda engine, payload: SimpleNamespace(id=9, full_name=payload.full_name),
    )
    monkeypatch.setattr(
        candidates_mod,
        "get_candidate_detail_service",
        lambda *a, **k: SimpleNamespace(id=9),
    )

    candidates_mod.create_candidate_service(MagicMock(), _candidate_payload())

    notif = capture.payload
    assert notif is not None
    assert notif.event_type == "candidate_assigned"
    assert notif.user_id == 22
    _assert_clear(notif, entity="Asha Verma", keyword="start screening", action_url_host="/candidates/9")


def test_duplicate_review_assigned_notification_is_specific(monkeypatch) -> None:
    capture = _Capture()
    monkeypatch.setattr(candidates_mod, "create_notification_service", capture)
    monkeypatch.setattr(
        candidates_mod,
        "find_candidate_by_id",
        lambda engine, cid: SimpleNamespace(id=cid, full_name="Asha Verma", duplicate_state="in-review"),
    )
    monkeypatch.setattr(
        candidates_mod,
        "find_user_by_id",
        lambda engine, uid: make_user_record(user_id=uid, primary_location_id=4),
    )
    monkeypatch.setattr(candidates_mod, "update_candidate_duplicate_state", lambda *a, **k: None)
    monkeypatch.setattr(candidates_mod, "insert_audit_log", lambda *a, **k: None)
    monkeypatch.setattr(
        candidates_mod,
        "create_duplicate_review_case",
        lambda **k: SimpleNamespace(
            id=3,
            candidate_id=11,
            matched_candidate_id=12,
            decision_status="approved",
            decision_notes="duplicate",
            requested_by_user_id=21,
            assigned_reviewer_user_id=22,
            created_at=datetime(2026, 9, 1),
            updated_at=datetime(2026, 9, 1),
        ),
    )
    monkeypatch.setattr(candidates_mod, "CandidateDuplicateReviewCaseResponse", _Passthrough)

    candidates_mod.create_candidate_duplicate_decision_service(
        MagicMock(),
        11,
        CandidateDuplicateDecisionPayload(
            decision="discard_draft",
            matched_candidate_id=12,
            decision_notes="duplicate profile",
            requested_by_user_id=21,
            assigned_reviewer_user_id=22,
        ),
    )

    notif = capture.payload
    assert notif is not None
    assert notif.event_type == "duplicate_review_assigned"
    assert notif.user_id == 22
    _assert_clear(
        notif,
        entity="Asha Verma",
        keyword="review case",
        action_url_host="/candidates/11/duplicate-review",
    )


def test_candidate_finalized_notification_is_specific(monkeypatch) -> None:
    capture = _Capture()
    monkeypatch.setattr(candidates_mod, "create_notification_service", capture)
    monkeypatch.setattr(
        candidates_mod,
        "find_candidate_by_id",
        lambda engine, cid: SimpleNamespace(id=cid, full_name="Asha Verma", duplicate_state="cleared"),
    )
    monkeypatch.setattr(
        candidates_mod,
        "find_requisition_by_id",
        lambda engine, rid: SimpleNamespace(
            id=rid,
            title="Senior Java Developer",
            location_id=4,
            primary_owner_user_id=22,
        ),
    )
    monkeypatch.setattr(
        candidates_mod,
        "count_candidate_applications_for_requisition",
        lambda *a, **k: 0,
    )
    monkeypatch.setattr(
        candidates_mod,
        "find_user_by_id",
        lambda engine, uid: make_user_record(user_id=uid, primary_location_id=4),
    )
    monkeypatch.setattr(
        candidates_mod,
        "finalize_candidate_into_requisition",
        lambda *a, **k: SimpleNamespace(
            candidate_id=11,
            requisition_id=7,
            application_id=500,
            current_stage="interview",
            application_status="active",
            finalized_at=datetime(2026, 9, 1),
        ),
    )
    monkeypatch.setattr(candidates_mod, "CandidateFinalizeResponse", _Passthrough)

    candidates_mod.finalize_candidate_service(
        MagicMock(),
        11,
        CandidateFinalizePayload(
            requisition_id=7,
            initial_stage="interview",
            owner_user_id=23,
            submitted_by_user_id=24,
            finalized_by_user_id=25,
        ),
    )

    notif = capture.payload
    assert notif is not None
    assert notif.event_type == "candidate_finalized"
    assert notif.user_id == 22
    _assert_clear(
        notif,
        entity="Asha Verma",
        keyword="confirm the move",
        action_url_host="/requisitions/7",
    )
    assert "Senior Java Developer" in notif.message


def test_candidate_owner_reassigned_notification_is_specific(monkeypatch) -> None:
    capture = _Capture()
    monkeypatch.setattr(candidates_mod, "create_notification_service", capture)
    monkeypatch.setattr(
        candidates_mod,
        "get_candidate_detail_service",
        lambda *a, **k: SimpleNamespace(
            full_name="Asha Verma",
            primary_owner_user_id=21,
            applications=[SimpleNamespace(location_id=4)],
        ),
    )
    monkeypatch.setattr(
        candidates_mod,
        "find_user_by_id",
        lambda engine, uid: make_user_record(user_id=uid, primary_location_id=4),
    )
    monkeypatch.setattr(candidates_mod, "count_active_candidate_applications", lambda *a, **k: 0)
    monkeypatch.setattr(candidates_mod, "update_candidate", lambda *a, **k: None)

    candidates_mod.reassign_candidate_owner_service(
        MagicMock(),
        11,
        CandidateOwnerReassignment(
            new_primary_owner_user_id=22,
            reason="Distributing workload",
            review_confirmed=True,
        ),
    )

    notif = capture.payload
    assert notif is not None
    assert notif.event_type == "candidate_owner_reassigned"
    assert notif.user_id == 22
    _assert_clear(
        notif,
        entity="Asha Verma",
        keyword="pick up",
        action_url_host="/candidates/11",
    )


# --- requisitions ----------------------------------------------------------

def _requisition_stub(**overrides) -> SimpleNamespace:
    base = dict(
        id=7,
        location_id=4,
        title="Senior Java Developer",
        client_name="TechNova",
        status="open",
        primary_owner_user_id=22,
        delivery_owner_user_id=None,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def test_requisition_created_notification_is_specific(monkeypatch) -> None:
    capture = _Capture()
    monkeypatch.setattr(requisitions_mod, "create_notification_service", capture)
    monkeypatch.setattr(
        requisitions_mod,
        "find_user_by_id",
        lambda engine, uid: make_user_record(user_id=uid, primary_location_id=4),
    )
    monkeypatch.setattr(
        requisitions_mod,
        "find_client_by_id",
        lambda engine, cid: SimpleNamespace(id=cid, status="active", location_id=4),
    )
    monkeypatch.setattr(requisitions_mod, "list_client_contacts", lambda *a, **k: [])
    monkeypatch.setattr(
        requisitions_mod,
        "create_requisition",
        lambda engine, payload: _requisition_stub(id=7, title=payload.title),
    )
    monkeypatch.setattr(requisitions_mod, "RequisitionResponse", _Passthrough)

    requisitions_mod.create_requisition_service(
        MagicMock(),
        SimpleNamespace(
            client_id=10,
            location_id=4,
            title="Senior Java Developer",
            primary_owner_user_id=22,
            delivery_owner_user_id=None,
            primary_contact_id=None,
            secondary_contact_id=None,
        ),
    )

    notif = capture.payload
    assert notif is not None
    assert notif.event_type == "requisition_created"
    assert notif.user_id == 22
    _assert_clear(
        notif,
        entity="Senior Java Developer",
        keyword="start sourcing",
        action_url_host="/requisitions/7",
    )
    assert "TechNova" in notif.message


def test_requisition_status_changed_notification_is_specific(monkeypatch) -> None:
    capture = _Capture()
    monkeypatch.setattr(requisitions_mod, "create_notification_service", capture)
    monkeypatch.setattr(
        requisitions_mod,
        "find_requisition_by_id",
        lambda engine, rid: _requisition_stub(id=rid, status="open"),
    )
    monkeypatch.setattr(
        requisitions_mod,
        "update_requisition_status",
        lambda *a, **k: _requisition_stub(status="on_hold"),
    )
    monkeypatch.setattr(requisitions_mod, "RequisitionResponse", _Passthrough)

    requisitions_mod.update_requisition_status_service(
        MagicMock(),
        7,
        SimpleNamespace(status="on_hold", reason="Budget on hold"),
    )

    notif = capture.payload
    assert notif is not None
    assert notif.event_type == "requisition_status_changed"
    assert notif.user_id == 22
    _assert_clear(
        notif,
        entity="Senior Java Developer",
        keyword="changes",
        action_url_host="/requisitions/7",
    )
    assert "open" in notif.message and "on_hold" in notif.message


def test_requisition_assigned_notification_is_specific(monkeypatch) -> None:
    capture = _Capture()
    monkeypatch.setattr(requisitions_mod, "create_notification_service", capture)
    monkeypatch.setattr(
        requisitions_mod,
        "find_requisition_by_id",
        lambda engine, rid: _requisition_stub(id=rid),
    )
    monkeypatch.setattr(
        requisitions_mod,
        "find_user_by_id",
        lambda engine, uid: make_user_record(user_id=uid, primary_location_id=4),
    )
    monkeypatch.setattr(
        requisitions_mod,
        "create_requisition_assignment",
        lambda *a, **k: SimpleNamespace(
            id=5,
            location_id=4,
            requisition_id=7,
            assigned_user_id=22,
            assignment_type="contributor",
            assigned_by_user_id=21,
            assigned_at=datetime(2026, 9, 1),
            status="active",
            created_at=datetime(2026, 9, 1),
            updated_at=datetime(2026, 9, 1),
        ),
    )
    monkeypatch.setattr(requisitions_mod, "RequisitionAssignmentResponse", _Passthrough)

    requisitions_mod.create_requisition_assignment_service(
        MagicMock(),
        7,
        RequisitionAssignmentCreate(assigned_user_id=22, assignment_type="contributor", assigned_by_user_id=21),
    )

    notif = capture.payload
    assert notif is not None
    assert notif.event_type == "requisition_assigned"
    assert notif.user_id == 22
    _assert_clear(
        notif,
        entity="Senior Java Developer",
        keyword="now own",
        action_url_host="/requisitions/7",
    )


def test_requisition_owner_reassigned_notification_is_specific(monkeypatch) -> None:
    capture = _Capture()
    monkeypatch.setattr(requisitions_mod, "create_notification_service", capture)
    monkeypatch.setattr(
        requisitions_mod,
        "find_requisition_by_id",
        lambda engine, rid: _requisition_stub(id=rid, primary_owner_user_id=30),
    )
    monkeypatch.setattr(
        requisitions_mod,
        "find_user_by_id",
        lambda engine, uid: make_user_record(user_id=uid, primary_location_id=4),
    )
    monkeypatch.setattr(requisitions_mod, "count_active_requisition_assignments", lambda *a, **k: 0)
    monkeypatch.setattr(requisitions_mod, "count_active_requisition_applications", lambda *a, **k: 0)
    monkeypatch.setattr(requisitions_mod, "update_requisition", lambda *a, **k: None)

    requisitions_mod.reassign_requisition_owners_service(
        MagicMock(),
        7,
        RequisitionOwnerReassignment(new_primary_owner_user_id=22, reason="Taking over"),
        auth_context=_auth_context(),
    )

    notif = capture.payload
    assert notif is not None
    assert notif.event_type == "requisition_owner_reassigned"
    assert notif.user_id == 22
    _assert_clear(
        notif,
        entity="Senior Java Developer",
        keyword="primary owner",
        action_url_host="/requisitions/7",
    )


# --- daily updates ----------------------------------------------------------

def test_daily_update_submitted_notification_is_specific(monkeypatch) -> None:
    capture = _Capture()
    monkeypatch.setattr(daily_updates_mod, "create_notification_service", capture)
    monkeypatch.setattr(
        daily_updates_mod,
        "find_user_by_id",
        lambda engine, uid: make_user_record(
            user_id=uid,
            full_name="Ravi Kumar",
            primary_role_code="recruiter",
            primary_location_id=4,
        ),
    )
    monkeypatch.setattr(
        daily_updates_mod,
        "find_requisition_by_id",
        lambda engine, rid: _requisition_stub(id=rid, title="Senior Java Developer"),
    )
    monkeypatch.setattr(daily_updates_mod, "has_user_requisition_link", lambda *a, **k: True)
    monkeypatch.setattr(
        daily_updates_mod,
        "count_daily_updates_for_user_requisition_date",
        lambda *a, **k: 0,
    )
    monkeypatch.setattr(
        daily_updates_mod,
        "create_daily_update",
        lambda *a, **k: SimpleNamespace(id=9),
    )
    monkeypatch.setattr(daily_updates_mod, "DailyUpdateResponse", _Passthrough)

    daily_updates_mod.create_daily_update_service(
        MagicMock(),
        SimpleNamespace(requisition_id=7, submitted_by_user_id=21, update_date="2026-09-22"),
    )

    notif = capture.payload
    assert notif is not None
    assert notif.event_type == "daily_update_submitted"
    assert notif.user_id == 22
    _assert_clear(
        notif,
        entity="Senior Java Developer",
        keyword="follow up",
        action_url_host="/daily-updates/9",
    )


# --- workflow actions -------------------------------------------------------

def test_workflow_nudge_default_message_is_specific(monkeypatch) -> None:
    action_item = SimpleNamespace(
        id=10,
        location_id=4,
        assigned_user_id=22,
        title="Confirm interview feedback",
        entity_type="candidate",
        entity_id=9,
        route_href="/candidates/9",
        overlay_key="confirm-interview",
    )
    capture = _Capture()
    monkeypatch.setattr(workflow_actions_mod, "create_notification", capture)
    monkeypatch.setattr(
        workflow_actions_mod,
        "find_workflow_action_item",
        lambda engine, aid: action_item,
    )
    monkeypatch.setattr(
        workflow_actions_mod,
        "create_workflow_action_event",
        lambda engine, **k: SimpleNamespace(
            id=5,
            action_item_id=10,
            overlay_key="confirm-interview",
            actor_user_id=1,
            action_type="nudge",
            event_status="sent",
            notes=None,
            payload={},
            next_route_href="/candidates/9",
            created_at=datetime(2026, 9, 1),
        ),
    )
    monkeypatch.setattr(workflow_actions_mod, "insert_audit_log", lambda *a, **k: None)
    monkeypatch.setattr(workflow_actions_mod, "WorkflowActionEventResponse", _Passthrough)

    workflow_actions_mod.nudge_workflow_action_service(
        MagicMock(),
        _auth_context(),
        10,
        WorkflowActionNudgeRequest(),
    )

    notif = capture.payload
    assert notif is not None
    assert notif.event_type == "workflow_action.nudge"
    assert notif.user_id == 22
    _assert_clear(
        notif,
        entity="Confirm interview feedback",
        keyword="still open",
        action_url_host="/candidates/9",
    )