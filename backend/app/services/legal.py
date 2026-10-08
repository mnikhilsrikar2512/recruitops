"""Legal versions and acceptance (Phase 5.1, decision I-7a).

Terms and Privacy are accepted by every user; the DPA once per company by
someone who can change company settings, on the company's behalf. A new
version (published by ops) makes everyone accept again. Production refuses
to start while any active document is still a placeholder.
"""
from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import Engine

from app.repositories.audit import insert_audit_log
from app.repositories.legal import (
    PER_COMPANY,
    accepted_versions,
    active_placeholders,
    find_active_document,
    list_active_documents,
    list_company_acceptances,
    record_acceptance,
)
from app.schemas.legal import (
    LegalAcceptanceCreate,
    LegalAcceptanceRecord,
    LegalDocumentResponse,
    LegalDocumentsResponse,
    LegalStatusItem,
    LegalStatusResponse,
)
from app.services import scope


def documents_service(engine: Engine) -> LegalDocumentsResponse:
    items = [LegalDocumentResponse(**doc) for doc in list_active_documents(engine)]
    return LegalDocumentsResponse(items=items, has_placeholders=any(item.is_placeholder for item in items))


def status_service(engine: Engine, auth_context, can_accept_company: bool) -> LegalStatusResponse:
    tenant_id = scope.tenant_id_of(auth_context)
    accepted = accepted_versions(engine, auth_context.user.id, tenant_id)
    items: list[LegalStatusItem] = []
    for doc in list_active_documents(engine):
        mine = accepted.get(doc["doc_type"])
        company = doc["doc_type"] in PER_COMPANY
        needs = mine is None or mine["version"] < doc["version"]
        items.append(LegalStatusItem(
            doc_type=doc["doc_type"],
            title=doc["title"],
            current_version=doc["version"],
            accepted_version=mine["version"] if mine else None,
            accepted_at=mine["accepted_at"] if mine else None,
            scope="company" if company else "user",
            needs_acceptance=needs,
            can_accept=can_accept_company if company else True,
            is_placeholder=doc["is_placeholder"],
        ))
    pending = [i.doc_type for i in items if i.needs_acceptance and i.can_accept and tenant_id is not None]
    company_pending = [i.doc_type for i in items if i.needs_acceptance and not i.can_accept]
    return LegalStatusResponse(items=items, pending=pending, company_pending=company_pending)


def accept_service(
    engine: Engine,
    auth_context,
    payload: LegalAcceptanceCreate,
    can_accept_company: bool,
    ip_address: str | None,
    user_agent: str | None,
) -> LegalStatusResponse:
    tenant_id = scope.tenant_id_of(auth_context)
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Legal acceptance belongs to a company user")
    document = find_active_document(engine, payload.doc_type)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="That document is not published")
    if document["version"] != payload.version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A newer version ({document['version']}) of this document is in force; read it and accept that one",
        )
    company = payload.doc_type in PER_COMPANY
    if company and not can_accept_company:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only a company admin can accept the DPA for the company")
    acceptance_id = record_acceptance(
        engine,
        tenant_id=int(tenant_id),
        user_id=auth_context.user.id,
        document=document,
        on_behalf_of_company=company,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    insert_audit_log(
        engine,
        actor_user_id=auth_context.user.id,
        location_id=auth_context.user.location_id,
        entity_type="legal_acceptance",
        entity_id=acceptance_id,
        action_type="legal.accepted",
        new_values={"doc_type": payload.doc_type, "version": payload.version, "on_behalf_of_company": company},
    )
    return status_service(engine, auth_context, can_accept_company)


def company_acceptances_service(engine: Engine, auth_context) -> list[LegalAcceptanceRecord]:
    tenant_id = scope.tenant_id_of(auth_context)
    if tenant_id is None:
        return []
    return [LegalAcceptanceRecord(**row) for row in list_company_acceptances(engine, int(tenant_id))]


def assert_no_placeholders_for_live(engine: Engine) -> None:
    """Go-live gate: production must not run on placeholder legal text."""
    placeholders = active_placeholders(engine)
    if placeholders:
        raise RuntimeError(
            "Refusing to start in production: legal documents are still placeholders ("
            + ", ".join(placeholders)
            + "). Publish counsel's text with backend/scripts/publish_legal.py."
        )
