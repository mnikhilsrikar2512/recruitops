import time
from functools import lru_cache
from typing import Callable

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import Engine

from app.core.rbac import COMPANY_SCOPE_CODE
from app.db.session import create_db_engine
from app.repositories.auth import list_resolved_permissions
from app.services import scope
from app.services.auth import AuthContext, get_auth_context_from_token

http_bearer = HTTPBearer(auto_error=False)

PERMISSION_ALIASES: dict[str, tuple[str, ...]] = {
    "location.read": ("location.read", "branch.read"),
    "location.create": ("location.create", "branch.create"),
    "location.update": ("location.update", "branch.update"),
    "candidate.resume.upload": ("candidate.resume.upload", "candidate.upload_resume"),
    "candidate.duplicate.check": ("candidate.duplicate.check", "candidate.handle_duplicate"),
    "candidate.duplicate.request_override": ("candidate.duplicate.request_override", "candidate.handle_duplicate"),
    "candidate.duplicate.link_existing": ("candidate.duplicate.link_existing", "candidate.handle_duplicate"),
    "candidate.duplicate.discard_draft": ("candidate.duplicate.discard_draft", "candidate.handle_duplicate"),
    "candidate.link_requisition": ("candidate.link_requisition", "candidate.update", "candidate.create"),
    "client.contact.read": ("client.contact.read", "client.read", "client.manage_contacts"),
    "client.contact.create": ("client.contact.create", "client.manage_contacts"),
    "client.contact.update": ("client.contact.update", "client.manage_contacts"),
    "assignment.read": ("assignment.read", "requisition.read", "requisition.assign"),
    "assignment.create": ("assignment.create", "requisition.assign"),
    "assignment.update": ("assignment.update", "requisition.assign"),
    "requisition.status.update": ("requisition.status.update", "requisition.update"),
    "pipeline.read.summary": ("pipeline.read.summary",),
    "pipeline.read.detail": ("pipeline.read.detail",),
    "pipeline.stage.move": ("pipeline.stage.move", "candidate.update"),
    "pipeline.stage.history.read": ("pipeline.stage.history.read",),
    "interview.read": ("interview.read", "pipeline.read.detail", "candidate.read"),
    "interview.create": ("interview.create", "pipeline.stage.move", "candidate.update"),
    "interview.feedback.submit": ("interview.feedback.submit", "pipeline.stage.move", "candidate.screen"),
    "offer.read": ("offer.read", "pipeline.read.detail", "candidate.read"),
    "offer.create": ("offer.create", "approval.request", "pipeline.stage.move"),
    "offer.decide": ("offer.decide", "approval.decide", "workflow_action.run"),
    "daily_update.read": (
        "daily_update.read",
        "report.read_recruiter",
        "report.read_hr",
        "report.read_manager",
        "report.read_admin",
        "report.submit_daily_update",
    ),
    "daily_update.create_main": ("daily_update.create_main", "report.submit_daily_update"),
    "meeting.read": ("meeting.read", "dashboard.read_my_work", "report.read_manager", "report.read_admin"),
    "meeting.create": ("meeting.create", "workflow_action.run", "dashboard.read_my_work"),
    "meeting.update": ("meeting.update", "workflow_action.run", "dashboard.read_my_work"),
    "dashboard.read_pipeline_summary": (
        "dashboard.read_pipeline_summary",
        "dashboard.view_admin",
        "dashboard.view_hr",
        "dashboard.view_manager",
        "dashboard.view_recruiter",
    ),
    "dashboard.read_my_work": (
        "dashboard.read_my_work",
        "dashboard.view_admin",
        "dashboard.view_hr",
        "dashboard.view_manager",
        "dashboard.view_recruiter",
    ),
    "notification.mark_read": ("notification.mark_read", "notification.read", "notification.manage"),
    "user.credentials.manage": ("user.credentials.manage", "user.manage_credentials"),
    "role.create": ("role.create",),
    "role.update": ("role.update",),
    "role.permissions.assign": ("role.permissions.assign",),
    "workflow_action.read": ("workflow_action.read", "dashboard.read_my_work", "dashboard.read_pipeline_summary"),
    "workflow_action.run": ("workflow_action.run", "pipeline.stage.move", "candidate.update"),
    "workflow_action.resolve": ("workflow_action.resolve", "pipeline.stage.move", "candidate.update"),
    "workflow_action.nudge": ("workflow_action.nudge", "notification.manage", "notification.mark_read"),
    "workflow_overlay.submit": ("workflow_overlay.submit", "workflow_action.run", "candidate.update"),
    "ai.use": ("ai.use",),
    "ai.agent.resume_screener": ("ai.agent.resume_screener",),
    "ai.agent.daily_brief": ("ai.agent.daily_brief",),
    "ai.agent.inbox_triage": ("ai.agent.inbox_triage",),
}

_permission_cache: dict[int, tuple[float, set[str]]] = {}
_PERMISSION_CACHE_TTL_SECONDS = 300


def _has_permission(resolved_permissions: set[str], required_code: str) -> bool:
    aliases = PERMISSION_ALIASES.get(required_code, (required_code,))
    return any(code in resolved_permissions for code in aliases)


def _get_cached_permissions(engine: Engine, user_id: int) -> set[str]:
    now = time.monotonic()
    cached = _permission_cache.get(user_id)
    if cached:
        cached_time, cached_perms = cached
        if now - cached_time < _PERMISSION_CACHE_TTL_SECONDS:
            return cached_perms
    perms = set(list_resolved_permissions(engine, user_id))
    _permission_cache[user_id] = (now, perms)
    return perms


def invalidate_permission_cache(user_id: int | None = None) -> None:
    if user_id is None:
        _permission_cache.clear()
    else:
        _permission_cache.pop(user_id, None)


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    return create_db_engine()


def get_current_auth_context(
    credentials: HTTPAuthorizationCredentials | None = Depends(http_bearer),
    engine: Engine = Depends(get_engine),
) -> AuthContext:
    if credentials is None or credentials.scheme.lower() != "bearer" or not credentials.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication is required")
    auth_context = get_auth_context_from_token(engine, credentials.credentials)
    # Company-wide reach is a GRANT (scope.company), not a role code (plan 2.5).
    auth_context.company_wide = COMPANY_SCOPE_CODE in resolved_permissions_for(engine, auth_context)
    return auth_context


def resolved_permissions_for(engine: Engine, auth_context: AuthContext) -> set[str]:
    """The caller's granted permission codes (cached briefly). Every route
    check goes through here — no role code bypasses it."""
    return _get_cached_permissions(engine, auth_context.user.id)


def require_permissions(*permission_codes: str) -> Callable[..., AuthContext]:
    def permission_dependency(
        auth_context: AuthContext = Depends(get_current_auth_context),
        engine: Engine = Depends(get_engine),
    ) -> AuthContext:
        resolved_permissions = resolved_permissions_for(engine, auth_context)
        missing_permissions = [
            code for code in permission_codes if not _has_permission(resolved_permissions, code)
        ]
        if missing_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required permission: {missing_permissions[0]}",
            )
        return auth_context

    return permission_dependency


def require_any_permission(*permission_codes: str) -> Callable[..., AuthContext]:
    def permission_dependency(
        auth_context: AuthContext = Depends(get_current_auth_context),
        engine: Engine = Depends(get_engine),
    ) -> AuthContext:
        resolved_permissions = resolved_permissions_for(engine, auth_context)
        if any(_has_permission(resolved_permissions, code) for code in permission_codes):
            return auth_context

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Missing one of the required permissions: {', '.join(permission_codes)}",
        )

    return permission_dependency


def require_location_scope(*field_names: str) -> Callable[..., AuthContext]:
    async def scope_dependency(
        request: Request,
        auth_context: AuthContext = Depends(get_current_auth_context),
        engine: Engine = Depends(get_engine),
    ) -> AuthContext:
        company_wide = scope.is_company_wide(auth_context)
        actor_location_id = auth_context.user.location_id
        if not company_wide and actor_location_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Location scope is not available for this user",
            )

        candidate_values: list[object] = []
        for field_name in field_names:
            if field_name in request.path_params:
                candidate_values.append(request.path_params[field_name])
            if field_name in request.query_params:
                candidate_values.append(request.query_params[field_name])

        if request.headers.get("content-type", "").startswith("application/json"):
            try:
                body = await request.json()
            except Exception:
                body = None
            if isinstance(body, dict):
                for field_name in field_names:
                    if field_name in body:
                        candidate_values.append(body[field_name])

        normalized_values = {
            int(value)
            for value in candidate_values
            if value not in (None, "", "null")
        }
        if not normalized_values:
            return auth_context

        # Company-wide users may name any office of THEIR company; everyone
        # else only their own office. Another company's office is never allowed.
        if any(not scope.can_reach_office(engine, auth_context, value) for value in normalized_values):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Location scope does not allow this action",
            )

        return auth_context

    return scope_dependency


# ── Row-level company (tenant) and office scoping ───────────────────────────
# Lists: non-company-wide users are pinned to their own office; every list is
# additionally filtered to the caller's company (filters.tenant_id). Direct-id
# routes: a record outside reach answers 404 so foreign ids can't be probed.
# The rules themselves live in app/services/scope.py.


def pinned_location_id(auth_context: AuthContext, requested: int | None) -> int | None:
    """Effective office filter: company-wide users keep what they asked for
    (None = every office of their company, enforced by the tenant filter);
    everyone else is pinned to their own office."""
    if scope.is_company_wide(auth_context):
        return requested
    return auth_context.user.location_id


def caller_tenant_id(auth_context: AuthContext) -> int | None:
    """The company every list must be restricted to."""
    return scope.tenant_id_of(auth_context)


def require_record_in_location(
    path_param: str,
    load_location_id: Callable[[Engine, int], int | None],
    not_found_detail: str,
) -> Callable[..., AuthContext]:
    """Dependency for direct-id routes: a record outside the caller's reach
    (another office, or another company) answers 404 (not 403) so ids in
    other companies cannot be discovered.

    ``load_location_id`` returns the record's location id and raises its own
    404 when the record does not exist."""

    def dependency(
        request: Request,
        auth_context: AuthContext = Depends(get_current_auth_context),
        engine: Engine = Depends(get_engine),
    ) -> AuthContext:
        record_id = int(request.path_params[path_param])
        scope.assert_office_reachable(engine, auth_context, load_location_id(engine, record_id), not_found_detail)
        return auth_context

    return dependency
