from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, status
from sqlalchemy import Engine

from app.api.deps import PERMISSION_ALIASES, get_current_auth_context, get_engine, require_permissions
from app.agents.registry import find_agent_by_id
from app.repositories.auth import list_resolved_permissions
from app.schemas.agent import (
    AgentCatalogResponse,
    AgentRunDecisionRequest,
    AgentRunListResponse,
    AgentRunRequest,
    AgentRunResponse,
)
from app.services.agents import (
    decide_agent_run_service,
    list_agent_runs_service,
    list_agents_service,
    run_agent_service,
)
from app.services.auth import AuthContext

router = APIRouter(dependencies=[Depends(get_current_auth_context)])


def _has_agent_resolved_permission(resolved_permissions: set[str], code: str) -> bool:
    aliases = PERMISSION_ALIASES.get(code, (code,))
    return any(alias in resolved_permissions for alias in aliases)


def _require_agent_run_permission(
    request: Request,
    auth_context: AuthContext = Depends(get_current_auth_context),
    engine: Engine = Depends(get_engine),
) -> AuthContext:
    if auth_context.user.role_code == "admin":
        return auth_context
    agent_id = request.path_params.get("agent_id")
    spec = find_agent_by_id(agent_id)
    if spec is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent was not found")
    resolved = set(list_resolved_permissions(engine, auth_context.user.id))
    if not _has_agent_resolved_permission(resolved, "ai.use") or not _has_agent_resolved_permission(
        resolved, spec.required_permission
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Missing required permission: {spec.required_permission}",
        )
    return auth_context


@router.get("/", response_model=AgentCatalogResponse)
def list_agents_endpoint(
    _auth: object = Depends(require_permissions("ai.use")),
) -> AgentCatalogResponse:
    return list_agents_service()


@router.post("/{agent_id}/run", response_model=AgentRunResponse)
def run_agent_endpoint(
    payload: AgentRunRequest,
    _auth: AuthContext = Depends(_require_agent_run_permission),
    agent_id: str = Path(..., min_length=1, max_length=100),
    auth_context: AuthContext = Depends(get_current_auth_context),
    engine: Engine = Depends(get_engine),
) -> AgentRunResponse:
    return run_agent_service(engine, auth_context, agent_id, payload)


@router.post("/runs/{run_id}/decision", response_model=AgentRunResponse)
def decide_agent_run_endpoint(
    payload: AgentRunDecisionRequest,
    _auth: object = Depends(require_permissions("ai.use")),
    run_id: int = Path(..., ge=1),
    auth_context: AuthContext = Depends(get_current_auth_context),
    engine: Engine = Depends(get_engine),
) -> AgentRunResponse:
    return decide_agent_run_service(engine, auth_context, run_id, payload)


@router.get("/runs", response_model=AgentRunListResponse)
def list_agent_runs_endpoint(
    _auth: object = Depends(require_permissions("ai.use")),
    agent_id: str | None = Query(default=None, max_length=100),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    auth_context: AuthContext = Depends(get_current_auth_context),
    engine: Engine = Depends(get_engine),
) -> AgentRunListResponse:
    return list_agent_runs_service(engine, auth_context, agent_id, page, page_size)