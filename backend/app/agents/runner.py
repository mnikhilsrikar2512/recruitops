"""Agent run orchestration (the AI orchestration service).

``run_agent`` resolves the agent, gathers read-only tool context, calls the
LLM provider, persists the run as a ``pending`` draft, and writes the audit
log. ``decide_agent_run`` records the human accept/reject decision. Nothing
here writes to domain tables — agents are draft-only by default.
"""
from __future__ import annotations

import logging

from fastapi import HTTPException, status
from sqlalchemy import Engine

logger = logging.getLogger(__name__)

from app.agents import tools
from app.agents.llm import get_llm_provider
from app.agents.registry import find_agent_by_id
from app.repositories.agents import (
    AgentRunRecord,
    create_agent_run,
    find_agent_run_by_id,
    update_agent_run_decision,
)
from app.repositories.audit import insert_audit_log
from app.schemas.agent import AgentRunDecisionRequest, AgentRunRequest
from app.services import scope
from app.services.auth import AuthContext


def _same_company(engine: Engine, auth_context: AuthContext, user_id: int | None) -> bool:
    try:
        scope.assert_user_in_tenant(engine, auth_context, user_id, "Agent run was not found")
    except HTTPException:
        return False
    return True


def run_agent(
    engine: Engine,
    auth_context: AuthContext,
    agent_id: str,
    payload: AgentRunRequest,
) -> AgentRunRecord:
    spec = find_agent_by_id(agent_id)
    if spec is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent was not found")

    try:
        context, input_refs = _collect_input(spec.id, engine, auth_context, payload)
        result = get_llm_provider().generate(spec.id, context, spec)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Agent run failed for agent_id=%s", spec.id)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Agent run failed while preparing the draft; try again.",
        ) from None

    run = create_agent_run(
        engine,
        agent_id=spec.id,
        actor_user_id=auth_context.user.id,
        location_id=auth_context.user.location_id,
        input_refs=input_refs,
        output_draft=result["output_draft"],
        output_summary=result["output_summary"],
    )
    insert_audit_log(
        engine,
        actor_user_id=auth_context.user.id,
        location_id=auth_context.user.location_id,
        entity_type="agent_run",
        entity_id=run.id,
        action_type="agent.run",
        new_values={"agent_id": spec.id, "output_summary": result["output_summary"]},
    )
    return run


def _collect_input(
    agent_id: str,
    engine: Engine,
    auth_context: AuthContext,
    payload: AgentRunRequest,
) -> tuple[dict, dict]:
    ctx = auth_context.user
    location_id = ctx.location_id
    # Phase 2: the read tools only know offices, not companies, so a company
    # admin's agent reads stay on their own office until the tools are made
    # tenant-aware (AI is off outside dev anyway — D-10).
    is_admin = False
    context: dict = {}
    input_refs: dict = {}

    if agent_id == "resume_screener":
        if payload.candidate_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="candidate_id is required to run the Resume Screener",
            )
        input_refs["candidate_id"] = payload.candidate_id
        candidate = tools.read_candidate(
            engine=engine,
            candidate_id=payload.candidate_id,
            location_id=location_id,
            is_admin=is_admin,
        )
        candidate["resume"] = tools.read_candidate_resume(
            engine=engine,
            candidate_id=payload.candidate_id,
            candidate=candidate,
        )
        context["candidate"] = candidate
        if payload.requisition_id:
            input_refs["requisition_id"] = payload.requisition_id
            context["requisition"] = tools.read_requisition(
                engine=engine,
                requisition_id=payload.requisition_id,
                location_id=location_id,
                is_admin=is_admin,
            )
        if payload.resume_document_id:
            input_refs["resume_document_id"] = payload.resume_document_id
            context["resume_document"] = tools.read_candidate_document(
                engine=engine,
                document_id=payload.resume_document_id,
                candidate_id=payload.candidate_id,
                location_id=location_id,
                is_admin=is_admin,
            )
        return context, input_refs

    if agent_id == "daily_brief":
        input_refs["scope"] = payload.scope
        context["scope"] = payload.scope
        context["updates"] = tools.read_daily_updates(
            engine=engine,
            scope=payload.scope,
            user_id=ctx.id,
            location_id=location_id,
            is_admin=is_admin,
            max_items=payload.max_items,
        )
        context["actions"] = tools.read_workflow_queue(
            engine=engine,
            actor_user_id=ctx.id,
            actor_location_id=location_id,
            actor_role_code=ctx.role_code,
            is_admin=is_admin,
            max_items=payload.max_items,
        )
        return context, input_refs

    if agent_id == "inbox_triage":
        status_name = payload.status or "unread"
        input_refs["status"] = status_name
        context["notifications"] = tools.read_notifications(
            engine=engine,
            user_id=ctx.id,
            status_name=status_name,
            max_items=payload.max_items,
        )
        return context, input_refs

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent was not found")


def decide_agent_run(
    engine: Engine,
    auth_context: AuthContext,
    run_id: int,
    payload: AgentRunDecisionRequest,
) -> AgentRunRecord:
    run = find_agent_run_by_id(engine, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent run was not found")

    if run.actor_user_id != auth_context.user.id and not (
        scope.is_company_wide(auth_context) and _same_company(engine, auth_context, run.actor_user_id)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Agent run access is not allowed",
        )
    if run.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Agent run has already been decided",
        )

    new_status = "accepted" if payload.decision == "accept" else "rejected"
    updated = update_agent_run_decision(
        engine,
        run_id,
        status=new_status,
        decided_by_user_id=auth_context.user.id,
        decision_notes=payload.decision_notes,
    )
    insert_audit_log(
        engine,
        actor_user_id=auth_context.user.id,
        location_id=auth_context.user.location_id,
        entity_type="agent_run",
        entity_id=run_id,
        action_type=f"agent.{payload.decision}",
        new_values={"agent_id": run.agent_id, "status": new_status},
    )
    return updated