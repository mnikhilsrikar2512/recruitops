from fastapi import HTTPException, status
from sqlalchemy import Engine

from app.agents.registry import AGENT_DEFINITIONS, find_agent_by_id
from app.agents.runner import decide_agent_run, run_agent
from app.api.deps import PERMISSION_ALIASES
from app.repositories.agents import find_agent_run_by_id, list_agent_runs
from app.repositories.auth import list_resolved_permissions
from app.schemas.agent import (
    AgentCatalogResponse,
    AgentInfo,
    AgentRunDecisionRequest,
    AgentRunListResponse,
    AgentRunRequest,
    AgentRunResponse,
)
from app.schemas.pagination import PaginationMeta
from app.services.auth import AuthContext


def _resolved_permissions(engine: Engine, auth_context: AuthContext) -> set[str]:
    return set(list_resolved_permissions(engine, auth_context.user.id))


def _guard_agent_permission(engine: Engine, auth_context: AuthContext, agent_id: str) -> None:
    spec = find_agent_by_id(agent_id)
    if spec is None:
        return
    # No role-code bypass (plan 2.5): admins pass by grant like everyone.
    # Resolve through PERMISSION_ALIASES exactly like require_permissions
    # does at the API layer, so both guards always reach the same verdict
    # (a legacy alias granted via role seed must not pass one guard and
    # fail the other).
    resolved = _resolved_permissions(engine, auth_context)
    aliases = PERMISSION_ALIASES.get(spec.required_permission, (spec.required_permission,))
    if not any(alias in resolved for alias in aliases):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Missing required permission: {spec.required_permission}",
        )


def list_agents_service() -> AgentCatalogResponse:
    return AgentCatalogResponse(
        items=[
            AgentInfo(
                id=definition.id,
                name=definition.name,
                job=definition.job,
                where_used=definition.where_used,
                output=definition.output,
                required_permission=definition.required_permission,
            )
            for definition in AGENT_DEFINITIONS
        ]
    )


def run_agent_service(
    engine: Engine,
    auth_context: AuthContext,
    agent_id: str,
    payload: AgentRunRequest,
) -> AgentRunResponse:
    run = run_agent(engine, auth_context, agent_id, payload)
    return AgentRunResponse.model_validate(run)


def decide_agent_run_service(
    engine: Engine,
    auth_context: AuthContext,
    run_id: int,
    payload: AgentRunDecisionRequest,
) -> AgentRunResponse:
    run = find_agent_run_by_id(engine, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent run was not found")
    _guard_agent_permission(engine, auth_context, run.agent_id)
    updated = decide_agent_run(engine, auth_context, run_id, payload)
    return AgentRunResponse.model_validate(updated)


def list_agent_runs_service(
    engine: Engine,
    auth_context: AuthContext,
    agent_id: str | None,
    page: int,
    page_size: int,
) -> AgentRunListResponse:
    if agent_id is not None and find_agent_by_id(agent_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent was not found")
    items, total = list_agent_runs(
        engine,
        actor_user_id=auth_context.user.id,
        agent_id=agent_id,
        page=page,
        page_size=page_size,
    )
    return AgentRunListResponse(
        items=[AgentRunResponse.model_validate(item) for item in items],
        meta=PaginationMeta(page=page, page_size=page_size, total=total),
    )