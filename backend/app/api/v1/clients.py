from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy import Engine

from app.api.deps import (
    caller_tenant_id,
    get_current_auth_context,
    get_engine,
    pinned_location_id,
    require_location_scope,
    require_permissions,
    require_record_in_location,
)
from app.schemas.client import (
    ClientContactCreate,
    ClientContactResponse,
    ClientContactUpdate,
    ClientCreate,
    ClientListFilters,
    ClientListResponse,
    ClientResponse,
    ClientUpdate,
)
from app.services.clients import (
    create_client_contact_service,
    create_client_service,
    get_client_detail_service,
    list_client_contacts_service,
    list_clients_service,
    update_client_contact_service,
    update_client_service,
)
from app.services.auth import AuthContext
from app.services import scope

router = APIRouter(dependencies=[Depends(get_current_auth_context)])

_scope_client = require_record_in_location(
    "client_id",
    lambda engine, client_id: get_client_detail_service(engine, client_id).location_id,
    "Client was not found",
)


@router.get("/", response_model=ClientListResponse)
def list_clients_endpoint(
    _auth: object = Depends(require_permissions("client.read")),
    auth_context: AuthContext = Depends(get_current_auth_context),
    _scope: object = Depends(require_location_scope("location_id")),
    location_id: int | None = Query(default=None, ge=1),
    status: str | None = Query(default=None),
    client_owner_user_id: int | None = Query(default=None, ge=1),
    business_source_owner_user_id: int | None = Query(default=None, ge=1),
    search: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    engine: Engine = Depends(get_engine),
) -> ClientListResponse:
    filters = ClientListFilters(
        location_id=pinned_location_id(auth_context, location_id),
        status=status,
        client_owner_user_id=client_owner_user_id,
        business_source_owner_user_id=business_source_owner_user_id,
        search=search,
        page=page,
        page_size=page_size,
    )
    filters.tenant_id = caller_tenant_id(auth_context)
    return list_clients_service(engine, filters)


@router.post("/", response_model=ClientResponse, status_code=201)
def create_client_endpoint(
    payload: ClientCreate,
    _auth: object = Depends(require_permissions("client.create")),
    _scope: object = Depends(require_location_scope("location_id")),
    auth_context: AuthContext = Depends(get_current_auth_context),
    engine: Engine = Depends(get_engine),
) -> ClientResponse:
    scope.assert_payload_refs_in_company(engine, auth_context, payload)
    return create_client_service(engine, payload)


@router.get("/{client_id}", response_model=ClientResponse)
def get_client_detail_endpoint(
    _auth: object = Depends(require_permissions("client.read")),
    _in_scope: object = Depends(_scope_client),
    client_id: int = Path(..., ge=1),
    engine: Engine = Depends(get_engine),
) -> ClientResponse:
    return get_client_detail_service(engine, client_id)


@router.patch("/{client_id}", response_model=ClientResponse)
def update_client_endpoint(
    payload: ClientUpdate,
    _auth: object = Depends(require_permissions("client.update")),
    _in_scope: object = Depends(_scope_client),
    client_id: int = Path(..., ge=1),
    auth_context: AuthContext = Depends(get_current_auth_context),
    engine: Engine = Depends(get_engine),
) -> ClientResponse:
    scope.assert_payload_refs_in_company(engine, auth_context, payload)
    return update_client_service(engine, client_id, payload)


@router.get("/{client_id}/contacts", response_model=list[ClientContactResponse])
def list_client_contacts_endpoint(
    _auth: object = Depends(require_permissions("client.contact.read")),
    _in_scope: object = Depends(_scope_client),
    client_id: int = Path(..., ge=1),
    engine: Engine = Depends(get_engine),
) -> list[ClientContactResponse]:
    return list_client_contacts_service(engine, client_id)


@router.post("/{client_id}/contacts", response_model=ClientContactResponse, status_code=201)
def create_client_contact_endpoint(
    payload: ClientContactCreate,
    _auth: object = Depends(require_permissions("client.contact.create")),
    _in_scope: object = Depends(_scope_client),
    client_id: int = Path(..., ge=1),
    auth_context: AuthContext = Depends(get_current_auth_context),
    engine: Engine = Depends(get_engine),
) -> ClientContactResponse:
    scope.assert_payload_refs_in_company(engine, auth_context, payload)
    return create_client_contact_service(engine, client_id, payload)


@router.patch("/contacts/{contact_id}", response_model=ClientContactResponse)
def update_client_contact_endpoint(
    payload: ClientContactUpdate,
    _auth: object = Depends(require_permissions("client.contact.update")),
    contact_id: int = Path(..., ge=1),
    auth_context: AuthContext = Depends(get_current_auth_context),
    engine: Engine = Depends(get_engine),
) -> ClientContactResponse:
    scope.assert_payload_refs_in_company(engine, auth_context, payload)
    return update_client_contact_service(engine, contact_id, payload)
