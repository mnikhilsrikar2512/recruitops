from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy import Engine

from app.api.deps import get_current_auth_context, get_engine, require_location_scope, require_permissions
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

router = APIRouter(dependencies=[Depends(get_current_auth_context)])


@router.get("/", response_model=ClientListResponse)
def list_clients_endpoint(
    _auth: object = Depends(require_permissions("client.read")),
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
        location_id=location_id,
        status=status,
        client_owner_user_id=client_owner_user_id,
        business_source_owner_user_id=business_source_owner_user_id,
        search=search,
        page=page,
        page_size=page_size,
    )
    return list_clients_service(engine, filters)


@router.post("/", response_model=ClientResponse, status_code=201)
def create_client_endpoint(
    payload: ClientCreate,
    _auth: object = Depends(require_permissions("client.create")),
    _scope: object = Depends(require_location_scope("location_id")),
    engine: Engine = Depends(get_engine),
) -> ClientResponse:
    return create_client_service(engine, payload)


@router.get("/{client_id}", response_model=ClientResponse)
def get_client_detail_endpoint(
    _auth: object = Depends(require_permissions("client.read")),
    client_id: int = Path(..., ge=1),
    engine: Engine = Depends(get_engine),
) -> ClientResponse:
    return get_client_detail_service(engine, client_id)


@router.patch("/{client_id}", response_model=ClientResponse)
def update_client_endpoint(
    payload: ClientUpdate,
    _auth: object = Depends(require_permissions("client.update")),
    client_id: int = Path(..., ge=1),
    engine: Engine = Depends(get_engine),
) -> ClientResponse:
    return update_client_service(engine, client_id, payload)


@router.get("/{client_id}/contacts", response_model=list[ClientContactResponse])
def list_client_contacts_endpoint(
    _auth: object = Depends(require_permissions("client.contact.read")),
    client_id: int = Path(..., ge=1),
    engine: Engine = Depends(get_engine),
) -> list[ClientContactResponse]:
    return list_client_contacts_service(engine, client_id)


@router.post("/{client_id}/contacts", response_model=ClientContactResponse, status_code=201)
def create_client_contact_endpoint(
    payload: ClientContactCreate,
    _auth: object = Depends(require_permissions("client.contact.create")),
    client_id: int = Path(..., ge=1),
    engine: Engine = Depends(get_engine),
) -> ClientContactResponse:
    return create_client_contact_service(engine, client_id, payload)


@router.patch("/contacts/{contact_id}", response_model=ClientContactResponse)
def update_client_contact_endpoint(
    payload: ClientContactUpdate,
    _auth: object = Depends(require_permissions("client.contact.update")),
    contact_id: int = Path(..., ge=1),
    engine: Engine = Depends(get_engine),
) -> ClientContactResponse:
    return update_client_contact_service(engine, contact_id, payload)
