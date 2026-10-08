"""Legal documents and acceptances (Phase 5.1).

GET  /legal/documents          public: the texts in force (sign-up and footer links)
GET  /legal/acceptances        what the caller still has to accept
POST /legal/acceptances        accept one document at its current version
GET  /legal/acceptances/company the company's acceptance record (admins)
"""
from fastapi import APIRouter, Depends, Request
from sqlalchemy import Engine

from app.api.deps import caller_has_permission, get_current_auth_context, get_engine, require_permissions
from app.schemas.legal import LegalAcceptanceCreate, LegalAcceptanceRecord, LegalDocumentsResponse, LegalStatusResponse
from app.services.auth import AuthContext
from app.services.legal import accept_service, company_acceptances_service, documents_service, status_service

router = APIRouter()

COMPANY_ACCEPT_PERMISSION = "settings.update"


@router.get("/documents", response_model=LegalDocumentsResponse)
def legal_documents_endpoint(engine: Engine = Depends(get_engine)) -> LegalDocumentsResponse:
    return documents_service(engine)


@router.get("/acceptances", response_model=LegalStatusResponse)
def legal_status_endpoint(
    auth_context: AuthContext = Depends(get_current_auth_context),
    engine: Engine = Depends(get_engine),
) -> LegalStatusResponse:
    return status_service(engine, auth_context, caller_has_permission(engine, auth_context, COMPANY_ACCEPT_PERMISSION))


@router.post("/acceptances", response_model=LegalStatusResponse, status_code=201)
def legal_accept_endpoint(
    payload: LegalAcceptanceCreate,
    request: Request,
    auth_context: AuthContext = Depends(get_current_auth_context),
    engine: Engine = Depends(get_engine),
) -> LegalStatusResponse:
    return accept_service(
        engine,
        auth_context,
        payload,
        caller_has_permission(engine, auth_context, COMPANY_ACCEPT_PERMISSION),
        request.client.host if request.client else None,
        request.headers.get("user-agent"),
    )


@router.get("/acceptances/company", response_model=list[LegalAcceptanceRecord])
def legal_company_acceptances_endpoint(
    auth_context: AuthContext = Depends(require_permissions("settings.read")),
    engine: Engine = Depends(get_engine),
) -> list[LegalAcceptanceRecord]:
    return company_acceptances_service(engine, auth_context)
