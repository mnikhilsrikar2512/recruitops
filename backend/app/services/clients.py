from fastapi import HTTPException, status
from sqlalchemy import Engine

from app.repositories.clients import (
    create_client,
    create_client_contact,
    find_client_by_code,
    find_client_by_id,
    find_client_contact_by_id,
    list_client_contacts,
    list_clients,
    update_client,
    update_client_contact,
)
from app.repositories.users import find_user_by_id, location_exists
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
from app.schemas.pagination import PaginationMeta


def _assert_client_owners(
    engine: Engine,
    location_id: int,
    client_owner_user_id: int | None = None,
    business_source_owner_user_id: int | None = None,
) -> None:
    if not location_exists(engine, location_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location was not found")

    if client_owner_user_id:
        owner = find_user_by_id(engine, client_owner_user_id)
        if not owner:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client owner user was not found")
        if owner.primary_location_id != location_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Client owner must belong to the same location",
            )

    if business_source_owner_user_id:
        source_owner = find_user_by_id(engine, business_source_owner_user_id)
        if not source_owner:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Business source owner user was not found")
        if source_owner.primary_location_id != location_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Business source owner must belong to the same location",
            )


def list_clients_service(engine: Engine, filters: ClientListFilters) -> ClientListResponse:
    items, total = list_clients(engine, filters)
    return ClientListResponse(
        items=[ClientResponse.model_validate(item) for item in items],
        meta=PaginationMeta(page=filters.page, page_size=filters.page_size, total=total),
    )


def create_client_service(engine: Engine, payload: ClientCreate) -> ClientResponse:
    if find_client_by_code(engine, payload.client_code):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Client code already exists")

    _assert_client_owners(
        engine,
        location_id=payload.location_id,
        client_owner_user_id=payload.client_owner_user_id,
        business_source_owner_user_id=payload.business_source_owner_user_id,
    )

    created = create_client(engine, payload)
    return ClientResponse.model_validate(created)


def get_client_detail_service(engine: Engine, client_id: int) -> ClientResponse:
    client = find_client_by_id(engine, client_id)
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client was not found")
    return ClientResponse.model_validate(client)


def update_client_service(engine: Engine, client_id: int, payload: ClientUpdate) -> ClientResponse:
    existing = find_client_by_id(engine, client_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client was not found")

    _assert_client_owners(
        engine,
        location_id=existing.location_id,
        client_owner_user_id=payload.client_owner_user_id,
        business_source_owner_user_id=payload.business_source_owner_user_id,
    )

    updated = update_client(engine, client_id, payload)
    return ClientResponse.model_validate(updated)


def list_client_contacts_service(engine: Engine, client_id: int) -> list[ClientContactResponse]:
    client = find_client_by_id(engine, client_id)
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client was not found")
    contacts = list_client_contacts(engine, client_id)
    return [ClientContactResponse.model_validate(contact) for contact in contacts]


def create_client_contact_service(
    engine: Engine,
    client_id: int,
    payload: ClientContactCreate,
) -> ClientContactResponse:
    client = find_client_by_id(engine, client_id)
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client was not found")
    created = create_client_contact(engine, client_id, client.location_id, payload)
    return ClientContactResponse.model_validate(created)


def update_client_contact_service(
    engine: Engine,
    contact_id: int,
    payload: ClientContactUpdate,
) -> ClientContactResponse:
    existing = find_client_contact_by_id(engine, contact_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client contact was not found")
    updated = update_client_contact(engine, contact_id, payload)
    return ClientContactResponse.model_validate(updated)
