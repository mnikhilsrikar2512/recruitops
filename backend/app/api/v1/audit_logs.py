"""Audit log viewer (Phase 5.4, PRD §9 /audit-logs). Company admins only
(audit_log.read); every row is limited to the caller's company."""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy import Engine

from app.api.deps import caller_tenant_id, get_engine, reject_unknown_query_params, require_permissions
from app.repositories.audit_logs import find_audit_log, list_audit_facets, list_audit_logs
from app.schemas.audit_logs import AuditLogDetail, AuditLogFacets, AuditLogItem, AuditLogListResponse
from app.schemas.pagination import PaginationMeta

router = APIRouter()


def _tenant(auth) -> int:
    tenant_id = caller_tenant_id(auth)
    if tenant_id is None:
        raise HTTPException(status_code=400, detail="The audit log belongs to a company; sign in as a company user")
    return int(tenant_id)


@router.get("/", response_model=AuditLogListResponse, dependencies=[Depends(reject_unknown_query_params)])
def list_audit_logs_endpoint(
    auth: object = Depends(require_permissions("audit_log.read")),
    actor_user_id: int | None = Query(default=None, ge=1),
    entity_type: str | None = Query(default=None, max_length=100),
    entity_id: int | None = Query(default=None, ge=1),
    action_type: str | None = Query(default=None, max_length=100),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    engine: Engine = Depends(get_engine),
) -> AuditLogListResponse:
    if date_from and date_to and date_from > date_to:
        raise HTTPException(status_code=422, detail="date_from must be on or before date_to")
    rows, total = list_audit_logs(
        engine, tenant_id=_tenant(auth), actor_user_id=actor_user_id, entity_type=entity_type,
        entity_id=entity_id, action_type=action_type, date_from=date_from, date_to=date_to,
        page=page, page_size=page_size,
    )
    return AuditLogListResponse(items=[AuditLogItem(**row) for row in rows],
                                meta=PaginationMeta(page=page, page_size=page_size, total=total))


@router.get("/facets", response_model=AuditLogFacets)
def audit_log_facets_endpoint(
    auth: object = Depends(require_permissions("audit_log.read")),
    engine: Engine = Depends(get_engine),
) -> AuditLogFacets:
    return AuditLogFacets(**list_audit_facets(engine, _tenant(auth)))


@router.get("/{audit_id}", response_model=AuditLogDetail)
def get_audit_log_endpoint(
    auth: object = Depends(require_permissions("audit_log.read")),
    audit_id: int = Path(..., ge=1),
    engine: Engine = Depends(get_engine),
) -> AuditLogDetail:
    row = find_audit_log(engine, _tenant(auth), audit_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Audit event was not found")
    return AuditLogDetail(**row)
