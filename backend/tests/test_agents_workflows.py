"""Tests for the V1 agentic AI capability (PRD §4.16).

Covers the registry, the mock LLM provider, read-only tool adapters with
tenant scope, the run orchestration (draft-only + audit), the human
accept/reject decision, per-agent permissions, and the HTTP surface.
"""
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.agents import llm, tools
from app.agents.registry import AGENT_DEFINITIONS
from app.agents.runner import decide_agent_run, run_agent
from app.repositories.agents import AgentRunRecord
from app.schemas.agent import AgentRunDecisionRequest, AgentRunRequest
from app.services.auth import AuthContext
from app.services import agents as agents_service
from tests.stubs import make_login_user_record


def _auth_context(user_id: int = 22, location_id: int | None = 4, role_code: str = "recruiter") -> AuthContext:
    user = make_login_user_record(
        user_id=user_id,
        role_code=role_code,
        location_id=location_id,
        full_name="Test User",
        business_title="Recruiter",
        role_id=1,
        role_name="Recruiter",
        location_code="NYC",
        location_name="New York",
        status="active",
        force_password_change_on_first_login=False,
    )
    return AuthContext(session_id=1, session_token_hash="tok_hash", user=user)


def make_agent_run(
    *,
    run_id: int = 1,
    agent_id: str = "resume_screener",
    actor_user_id: int = 22,
    location_id: int | None = 4,
    input_refs: dict | None = None,
    output_draft: dict | None = None,
    output_summary: str = "Agent summary",
    status: str = "pending",
    decided_by_user_id: int | None = None,
    decided_at=None,
    decision_notes: str | None = None,
) -> AgentRunRecord:
    return AgentRunRecord(
        id=run_id,
        agent_id=agent_id,
        actor_user_id=actor_user_id,
        location_id=location_id,
        input_refs=input_refs or {},
        output_draft=output_draft or {},
        output_summary=output_summary,
        status=status,
        decided_by_user_id=decided_by_user_id,
        decided_at=decided_at,
        decision_notes=decision_notes,
        created_at=datetime(2026, 1, 1),
        updated_at=datetime(2026, 1, 1),
    )


def _mock_engine() -> MagicMock:
    return MagicMock()


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

def test_registry_exposes_exactly_three_v1_agents() -> None:
    agent_ids = [definition.id for definition in AGENT_DEFINITIONS]
    assert agent_ids == ["resume_screener", "daily_brief", "inbox_triage"]
    for definition in AGENT_DEFINITIONS:
        assert definition.required_permission == f"ai.agent.{definition.id}"


# ---------------------------------------------------------------------------
# Mock LLM provider
# ---------------------------------------------------------------------------

def test_mock_provider_unknown_provider_raises() -> None:
    with pytest.raises(NotImplementedError):
        llm.get_llm_provider("openai")


class TestMockResumeScreener:
    def test_draft_without_requisition_lists_skills_for_review(self) -> None:
        provider = llm.MockLLMProvider()
        result = provider.generate(
            "resume_screener",
            {"candidate": {"full_name": "Elena K.", "current_designation": "Senior Engineer"}},
            AGENT_DEFINITIONS[0],
        )
        assert result["output_draft"]["profile"]["full_name"] == "Elena K."
        assert result["output_draft"]["match_score"] is None
        assert "no requisition selected" in result["output_draft"]["match_notes"][0].lower()

    def test_match_score_uses_must_have_skills(self) -> None:
        provider = llm.MockLLMProvider()
        context = {
            "candidate": {"full_name": "Elena", "current_designation": "Senior Frontend Engineer", "current_company": "Acme"},
            "requisition": {"title": "Frontend Engineer", "must_have_skills": ["frontend", "react"]},
        }
        result = provider.generate("resume_screener", context, AGENT_DEFINITIONS[0])
        assert result["output_draft"]["extracted_skills"] == ["frontend"]
        assert result["output_draft"]["match_score"] == 0.5
        assert "50%" in result["output_summary"]


class TestMockDailyBrief:
    def test_draft_includes_stats_and_focus_items(self) -> None:
        provider = llm.MockLLMProvider()
        context = {
            "scope": "me",
            "updates": [
                {"profiles_sourced_count": 3, "profiles_screened_count": 2, "blockers": "Awaiting JD approval"},
            ],
            "actions": [{"title": "Screen 3 candidates", "priority": "high", "entity_type": "candidate"}],
        }
        result = provider.generate("daily_brief", context, AGENT_DEFINITIONS[1])
        assert result["output_draft"]["stats"]["profiles_sourced"] == 3
        assert result["output_draft"]["blockers"] == ["Awaiting JD approval"]
        assert result["output_draft"]["focus_items"][0]["title"] == "Screen 3 candidates"


class TestMockInboxTriage:
    def test_queue_sorted_by_priority(self) -> None:
        provider = llm.MockLLMProvider()
        context = {
            "notifications": [
                {"id": 1, "priority": "normal", "title": "Update", "message": "m", "module_name": "pipeline", "entity_type": "candidate"},
                {"id": 2, "priority": "critical", "title": "Urgent", "message": "m", "module_name": "approvals", "entity_type": "approval"},
                {"id": 3, "priority": "high", "title": "High", "message": "m", "module_name": "offers", "entity_type": "offer"},
            ],
        }
        result = provider.generate("inbox_triage", context, AGENT_DEFINITIONS[2])
        queue = result["output_draft"]["queue"]
        assert [item["id"] for item in queue] == [2, 3, 1]
        assert queue[0]["what"] == "Urgent"
        assert "next" in queue[0]


# ---------------------------------------------------------------------------
# Tool adapters (tenant scope)
# ---------------------------------------------------------------------------

class TestToolAdapters:
    def test_read_candidate_not_found_raises_404(self, monkeypatch) -> None:
        monkeypatch.setattr("app.agents.tools.find_candidate_by_id", lambda engine, candidate_id: None)
        with pytest.raises(HTTPException) as exc:
            tools.read_candidate(engine=_mock_engine(), candidate_id=5, location_id=4, is_admin=False)
        assert exc.value.status_code == 404

    def test_read_requisition_scoped_out_raises_403(self, monkeypatch) -> None:
        requisition = SimpleNamespace(
            id=3, location_id=9, title="R", status="open", priority="high", client_name="c",
            openings_count=1, work_mode=None, employment_type=None, job_description="d",
            must_have_skills=[], good_to_have_skills=[],
        )
        monkeypatch.setattr("app.agents.tools.find_requisition_by_id", lambda engine, requisition_id: requisition)
        with pytest.raises(HTTPException) as exc:
            tools.read_requisition(engine=_mock_engine(), requisition_id=3, location_id=4, is_admin=False)
        assert exc.value.status_code == 403

    def test_read_requisition_admin_bypasses_scope(self, monkeypatch) -> None:
        requisition = SimpleNamespace(
            id=3, location_id=9, title="R", status="open", priority="high", client_name="c",
            openings_count=1, work_mode=None, employment_type=None, job_description="d",
            must_have_skills=["sql"], good_to_have_skills=[],
        )
        monkeypatch.setattr("app.agents.tools.find_requisition_by_id", lambda engine, requisition_id: requisition)
        data = tools.read_requisition(engine=_mock_engine(), requisition_id=3, location_id=4, is_admin=True)
        assert data["location_id"] == 9

    def test_read_candidate_scoped_out_via_applications_raises_403(self, monkeypatch) -> None:
        candidate = SimpleNamespace(
            id=5, full_name="E", email=None, phone=None, current_company=None,
            current_designation=None, total_experience_years=None, notice_period_days=None,
            source_type=None, source_detail=None, duplicate_state="none", profile_status="new",
            intake_stage="intake",
        )
        application = SimpleNamespace(location_id=9)
        monkeypatch.setattr("app.agents.tools.find_candidate_by_id", lambda engine, candidate_id: candidate)
        monkeypatch.setattr("app.agents.tools.list_candidate_applications", lambda engine, candidate_id: [application])
        with pytest.raises(HTTPException) as exc:
            tools.read_candidate(engine=_mock_engine(), candidate_id=5, location_id=4, is_admin=False)
        assert exc.value.status_code == 403


# ---------------------------------------------------------------------------
# Runner: run_agent (draft-only + audit)
# ---------------------------------------------------------------------------

class TestRunAgent:
    def test_unknown_agent_raises_404(self) -> None:
        with pytest.raises(HTTPException) as exc:
            run_agent(_mock_engine(), _auth_context(), "ghost_agent", AgentRunRequest())
        assert exc.value.status_code == 404

    def test_resume_screener_requires_candidate(self) -> None:
        with pytest.raises(HTTPException) as exc:
            run_agent(_mock_engine(), _auth_context(), "resume_screener", AgentRunRequest())
        assert exc.value.status_code == 422

    def test_resume_screener_persists_draft_and_audits(self, monkeypatch) -> None:
        monkeypatch.setattr(
            "app.agents.runner.tools.read_candidate",
            lambda **kwargs: {
                "full_name": "Elena K.",
                "current_designation": "Senior Frontend Engineer",
                "current_company": "Acme",
            },
        )
        monkeypatch.setattr(
            "app.agents.runner.tools.read_candidate_resume",
            lambda **kwargs: {"resume_file_name": "elena.pdf", "resume_file_path": "docs/elena.pdf", "resume_uploaded_at": None},
        )
        captures = {}
        monkeypatch.setattr("app.agents.runner.create_agent_run", _capture_create(captures))
        monkeypatch.setattr("app.agents.runner.insert_audit_log", lambda *args, **kwargs: captures.__setitem__("audit", kwargs) or None)

        result = run_agent(
            _mock_engine(),
            _auth_context(),
            "resume_screener",
            AgentRunRequest(candidate_id=5),
        )
        assert result.status == "pending"
        assert captures["input_refs"] == {"candidate_id": 5}
        assert captures["output_draft"]["profile"]["full_name"] == "Elena K."
        assert captures["audit"]["action_type"] == "agent.run"
        assert captures["audit"]["entity_id"] == result.id

    def test_resume_screener_with_requisition_includes_match(self, monkeypatch) -> None:
        monkeypatch.setattr(
            "app.agents.runner.tools.read_candidate",
            lambda **kwargs: {"full_name": "Elena", "current_designation": "Frontend Engineer", "current_company": "Acme"},
        )
        monkeypatch.setattr(
            "app.agents.runner.tools.read_candidate_resume",
            lambda **kwargs: {"resume_file_name": None, "resume_file_path": None, "resume_uploaded_at": None},
        )
        monkeypatch.setattr(
            "app.agents.runner.tools.read_requisition",
            lambda **kwargs: {"title": "Frontend Engineer", "must_have_skills": ["frontend", "react"]},
        )
        captures = {}
        monkeypatch.setattr("app.agents.runner.create_agent_run", _capture_create(captures))
        monkeypatch.setattr("app.agents.runner.insert_audit_log", lambda *args, **kwargs: None)

        run_agent(
            _mock_engine(),
            _auth_context(),
            "resume_screener",
            AgentRunRequest(candidate_id=5, requisition_id=9),
        )
        assert captures["input_refs"] == {"candidate_id": 5, "requisition_id": 9}
        assert captures["output_draft"]["extracted_skills"] == ["frontend"]

    def test_daily_brief_uses_scope(self, monkeypatch) -> None:
        captures = {"updates_kwargs": None, "queue_kwargs": None}
        monkeypatch.setattr(
            "app.agents.runner.tools.read_daily_updates",
            lambda **kwargs: captures.__setitem__("updates_kwargs", kwargs) or [],
        )
        monkeypatch.setattr(
            "app.agents.runner.tools.read_workflow_queue",
            lambda **kwargs: captures.__setitem__("queue_kwargs", kwargs) or [],
        )
        create_captures = {}
        monkeypatch.setattr("app.agents.runner.create_agent_run", _capture_create(create_captures))
        monkeypatch.setattr("app.agents.runner.insert_audit_log", lambda *args, **kwargs: None)

        run_agent(_mock_engine(), _auth_context(), "daily_brief", AgentRunRequest(scope="me"))
        assert captures["updates_kwargs"]["scope"] == "me"
        assert captures["updates_kwargs"]["user_id"] == 22
        assert captures["queue_kwargs"]["actor_user_id"] == 22
        assert create_captures["input_refs"] == {"scope": "me"}

    def test_inbox_triage_reads_unread_by_default(self, monkeypatch) -> None:
        captures = {}
        monkeypatch.setattr(
            "app.agents.runner.tools.read_notifications",
            lambda **kwargs: captures.update(kwargs) or [],
        )
        create_captures = {}
        monkeypatch.setattr("app.agents.runner.create_agent_run", _capture_create(create_captures))
        monkeypatch.setattr("app.agents.runner.insert_audit_log", lambda *args, **kwargs: None)

        run_agent(_mock_engine(), _auth_context(), "inbox_triage", AgentRunRequest())
        assert captures["status_name"] == "unread"
        assert create_captures["input_refs"] == {"status": "unread"}


def _capture_create(captures: dict):
    def _fake_create(engine, *, agent_id, actor_user_id, location_id, input_refs, output_draft, output_summary):
        captures["agent_id"] = agent_id
        captures["actor_user_id"] = actor_user_id
        captures["location_id"] = location_id
        captures["input_refs"] = input_refs
        captures["output_draft"] = output_draft
        captures["output_summary"] = output_summary
        return make_agent_run(
            run_id=7,
            agent_id=agent_id,
            actor_user_id=actor_user_id,
            location_id=location_id,
            input_refs=input_refs,
            output_draft=output_draft,
            output_summary=output_summary,
        )

    return _fake_create


# ---------------------------------------------------------------------------
# Runner: decide_agent_run (human-in-the-loop)
# ---------------------------------------------------------------------------

class TestDecideAgentRun:
    def test_accept_marks_run_and_audits(self, monkeypatch) -> None:
        full_run = make_agent_run(run_id=7, status="accepted", decided_by_user_id=22)
        monkeypatch.setattr("app.agents.runner.find_agent_run_by_id", lambda engine, run_id: make_agent_run(run_id=7))
        monkeypatch.setattr("app.agents.runner.update_agent_run_decision", lambda *a, **kw: full_run)
        audit = {}
        monkeypatch.setattr("app.agents.runner.insert_audit_log", lambda *args, **kwargs: audit.update(kwargs))

        result = decide_agent_run(
            _mock_engine(),
            _auth_context(),
            7,
            AgentRunDecisionRequest(decision="accept", decision_notes="Looks good"),
        )
        assert result.status == "accepted"
        assert audit["action_type"] == "agent.accept"

    def test_reject_marks_rejected(self, monkeypatch) -> None:
        full_run = make_agent_run(run_id=7, status="rejected", decided_by_user_id=22)
        monkeypatch.setattr("app.agents.runner.find_agent_run_by_id", lambda engine, run_id: make_agent_run(run_id=7))
        monkeypatch.setattr("app.agents.runner.update_agent_run_decision", lambda *a, **kw: full_run)
        monkeypatch.setattr("app.agents.runner.insert_audit_log", lambda *args, **kwargs: None)

        result = decide_agent_run(_mock_engine(), _auth_context(), 7, AgentRunDecisionRequest(decision="reject"))
        assert result.status == "rejected"

    def test_run_not_found_raises_404(self, monkeypatch) -> None:
        monkeypatch.setattr("app.agents.runner.find_agent_run_by_id", lambda engine, run_id: None)
        with pytest.raises(HTTPException) as exc:
            decide_agent_run(_mock_engine(), _auth_context(), 7, AgentRunDecisionRequest(decision="accept"))
        assert exc.value.status_code == 404

    def test_actor_cannot_decide_foreign_run(self, monkeypatch) -> None:
        monkeypatch.setattr(
            "app.agents.runner.find_agent_run_by_id",
            lambda engine, run_id: make_agent_run(run_id=7, actor_user_id=99),
        )
        with pytest.raises(HTTPException) as exc:
            decide_agent_run(_mock_engine(), _auth_context(user_id=22), 7, AgentRunDecisionRequest(decision="accept"))
        assert exc.value.status_code == 403

    def test_already_decided_run_raises_409(self, monkeypatch) -> None:
        monkeypatch.setattr(
            "app.agents.runner.find_agent_run_by_id",
            lambda engine, run_id: make_agent_run(run_id=7, status="accepted"),
        )
        with pytest.raises(HTTPException) as exc:
            decide_agent_run(_mock_engine(), _auth_context(), 7, AgentRunDecisionRequest(decision="accept"))
        assert exc.value.status_code == 409


# ---------------------------------------------------------------------------
# Service layer
# ---------------------------------------------------------------------------

class TestAgentsService:
    def test_catalog_returns_three_agents(self) -> None:
        catalog = agents_service.list_agents_service()
        assert len(catalog.items) == 3
        assert catalog.items[0].id == "resume_screener"

    def test_decide_service_requires_per_agent_permission(self, monkeypatch) -> None:
        monkeypatch.setattr(
            "app.services.agents.find_agent_run_by_id",
            lambda engine, run_id: make_agent_run(run_id=7, agent_id="resume_screener"),
        )
        monkeypatch.setattr("app.services.agents.list_resolved_permissions", lambda engine, user_id: ["ai.use"])
        with pytest.raises(HTTPException) as exc:
            agents_service.decide_agent_run_service(
                _mock_engine(),
                _auth_context(role_code="recruiter"),
                7,
                AgentRunDecisionRequest(decision="accept"),
            )
        assert exc.value.status_code == 403

    def test_decide_service_allows_per_agent_permission(self, monkeypatch) -> None:
        run = make_agent_run(run_id=7, agent_id="resume_screener")
        monkeypatch.setattr("app.services.agents.find_agent_run_by_id", lambda engine, run_id: run)
        monkeypatch.setattr(
            "app.services.agents.list_resolved_permissions",
            lambda engine, user_id: ["ai.use", "ai.agent.resume_screener"],
        )
        decided = make_agent_run(run_id=7, agent_id="resume_screener", status="accepted", decided_by_user_id=22)
        monkeypatch.setattr("app.services.agents.decide_agent_run", lambda *args, **kwargs: decided)

        response = agents_service.decide_agent_run_service(
            _mock_engine(),
            _auth_context(role_code="recruiter"),
            7,
            AgentRunDecisionRequest(decision="accept"),
        )
        assert response.status == "accepted"

    def test_list_runs_unknown_agent_raises_404(self) -> None:
        with pytest.raises(HTTPException) as exc:
            agents_service.list_agent_runs_service(_mock_engine(), _auth_context(), "ghost", 1, 20)
        assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# HTTP surface
# ---------------------------------------------------------------------------

def _make_app(auth_ctx: AuthContext | None = None) -> tuple[object, TestClient]:
    from app.api.deps import get_current_auth_context, get_engine
    from app.main import create_application

    get_engine.cache_clear()
    app = create_application()
    app.dependency_overrides[get_engine] = lambda: _mock_engine()
    if auth_ctx is not None:
        app.dependency_overrides[get_current_auth_context] = lambda: auth_ctx
    return app, TestClient(app, raise_server_exceptions=False)


class TestAgentsApi:
    def test_catalog_requires_ai_use(self, monkeypatch) -> None:
        monkeypatch.setattr("app.api.deps.list_resolved_permissions", lambda engine, user_id: [])
        _, client = _make_app(_auth_context(role_code="recruiter"))
        assert client.get("/api/v1/agents").status_code == 403

    def test_catalog_returns_agents(self) -> None:
        _, client = _make_app(_auth_context(role_code="admin"))
        response = client.get("/api/v1/agents")
        assert response.status_code == 200
        assert [item["id"] for item in response.json()["items"]] == [
            "resume_screener",
            "daily_brief",
            "inbox_triage",
        ]

    def test_run_requires_per_agent_permission(self, monkeypatch) -> None:
        monkeypatch.setattr("app.api.v1.agents.list_resolved_permissions", lambda engine, user_id: ["ai.use"])
        _, client = _make_app(_auth_context(role_code="recruiter"))
        response = client.post("/api/v1/agents/resume_screener/run", json={"candidate_id": 5})
        assert response.status_code == 403

    def test_run_unknown_agent_raises_404(self, monkeypatch) -> None:
        monkeypatch.setattr("app.api.v1.agents.list_resolved_permissions", lambda engine, user_id: ["ai.use"])
        _, client = _make_app(_auth_context(role_code="recruiter"))
        response = client.post("/api/v1/agents/ghost/run", json={})
        assert response.status_code == 404

    def test_run_returns_draft(self, monkeypatch) -> None:
        run = make_agent_run(run_id=7, agent_id="resume_screener", input_refs={"candidate_id": 5})
        monkeypatch.setattr("app.services.agents.run_agent", lambda engine, auth_context, agent_id, payload: run)
        _, client = _make_app(_auth_context(role_code="admin"))
        response = client.post("/api/v1/agents/resume_screener/run", json={"candidate_id": 5})
        assert response.status_code == 200
        body = response.json()
        assert body["agent_id"] == "resume_screener"
        assert body["status"] == "pending"
        assert body["input_refs"] == {"candidate_id": 5}

    def test_decision_requires_per_agent_permission(self, monkeypatch) -> None:
        monkeypatch.setattr(
            "app.services.agents.find_agent_run_by_id",
            lambda engine, run_id: make_agent_run(run_id=7, agent_id="resume_screener"),
        )
        monkeypatch.setattr("app.services.agents.list_resolved_permissions", lambda engine, user_id: ["ai.use"])
        _, client = _make_app(_auth_context(role_code="recruiter"))
        response = client.post("/api/v1/agents/runs/7/decision", json={"decision": "accept"})
        assert response.status_code == 403

    def test_decision_returns_accepted(self, monkeypatch) -> None:
        pending = make_agent_run(run_id=7, agent_id="resume_screener")
        accepted = make_agent_run(run_id=7, agent_id="resume_screener", status="accepted", decided_by_user_id=22)
        monkeypatch.setattr("app.services.agents.find_agent_run_by_id", lambda engine, run_id: pending)
        monkeypatch.setattr("app.services.agents.decide_agent_run", lambda *args, **kwargs: accepted)
        _, client = _make_app(_auth_context(role_code="admin"))
        response = client.post(
            "/api/v1/agents/runs/7/decision",
            json={"decision": "accept", "decision_notes": "ok"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "accepted"
        assert body["decided_by_user_id"] == 22

    def test_list_runs_requires_ai_use(self, monkeypatch) -> None:
        monkeypatch.setattr("app.api.deps.list_resolved_permissions", lambda engine, user_id: [])
        _, client = _make_app(_auth_context(role_code="recruiter"))
        assert client.get("/api/v1/agents/runs").status_code == 403

    def test_list_runs_returns_paginated(self, monkeypatch) -> None:
        run = make_agent_run(run_id=7, agent_id="daily_brief")
        monkeypatch.setattr(
            "app.services.agents.list_agent_runs",
            lambda engine, *, actor_user_id, agent_id, page, page_size: ([run], 1),
        )
        _, client = _make_app(_auth_context(role_code="admin"))
        response = client.get("/api/v1/agents/runs")
        assert response.status_code == 200
        body = response.json()
        assert len(body["items"]) == 1
        assert body["meta"]["total"] == 1
        assert body["items"][0]["agent_id"] == "daily_brief"