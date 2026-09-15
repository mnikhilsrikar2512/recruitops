from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import Engine, text
from sqlalchemy.engine import RowMapping

from app.schemas.client import (
    ClientContactCreate,
    ClientContactUpdate,
    ClientCreate,
    ClientListFilters,
    ClientUpdate,
)


@dataclass
class ClientRecord:
    id: int
    location_id: int
    client_code: str | None
    client_name: str
    industry: str | None
    status: str
    business_source_owner_user_id: int | None
    business_source_owner_name: str | None
    client_owner_user_id: int | None
    client_owner_name: str | None
    placement_fee_pct: float | None
    notes: str | None
    created_by_user_id: int | None
    created_at: object
    updated_at: object


@dataclass
class ClientContactRecord:
    id: int
    client_id: int
    location_id: int | None
    contact_name: str
    designation: str | None
    email: str | None
    phone: str | None
    is_primary_contact: bool
    is_secondary_contact: bool
    status: str
    notes: str | None
    created_by_user_id: int | None
    created_at: object
    updated_at: object


def _map_client(row: RowMapping) -> ClientRecord:
    return ClientRecord(
        id=row["id"],
        location_id=row["location_id"],
        client_code=row["client_code"],
        client_name=row["client_name"],
        industry=row["industry"],
        status=row["status"],
        business_source_owner_user_id=row["business_source_owner_user_id"],
        business_source_owner_name=row["business_source_owner_name"],
        client_owner_user_id=row["client_owner_user_id"],
        client_owner_name=row["client_owner_name"],
        placement_fee_pct=(
            float(row["placement_fee_pct"]) if row["placement_fee_pct"] is not None else None
        ),
        notes=row["notes"],
        created_by_user_id=row["created_by_user_id"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _map_client_contact(row: RowMapping) -> ClientContactRecord:
    return ClientContactRecord(
        id=row["id"],
        client_id=row["client_id"],
        location_id=row["location_id"],
        contact_name=row["contact_name"],
        designation=row["designation"],
        email=row["email"],
        phone=row["phone"],
        is_primary_contact=row["is_primary_contact"],
        is_secondary_contact=row["is_secondary_contact"],
        status=row["status"],
        notes=row["notes"],
        created_by_user_id=row["created_by_user_id"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def list_clients(engine: Engine, filters: ClientListFilters) -> tuple[list[ClientRecord], int]:
    query = text(
        """
        WITH filtered_clients AS (
          SELECT
            c.id,
            c.branch_id AS location_id,
            CAST(NULL AS NVARCHAR(50)) AS client_code,
            c.name AS client_name,
            c.industry,
            c.status,
            c.placement_fee_pct,
            c.account_manager_user_id AS business_source_owner_user_id,
            source_owner.full_name AS business_source_owner_name,
            c.account_manager_user_id AS client_owner_user_id,
            client_owner.full_name AS client_owner_name,
            c.notes,
            CAST(NULL AS BIGINT) AS created_by_user_id,
            c.created_at,
            c.updated_at,
            COUNT(*) OVER() AS total_count
          FROM dbo.client_companies AS c
          LEFT JOIN dbo.users AS source_owner
            ON source_owner.id = c.account_manager_user_id
          LEFT JOIN dbo.users AS client_owner
            ON client_owner.id = c.account_manager_user_id
          WHERE (:location_id IS NULL OR c.branch_id = :location_id)
          AND (:status IS NULL OR c.status = :status)
          AND (:client_owner_user_id IS NULL OR c.account_manager_user_id = :client_owner_user_id)
          AND (
            :business_source_owner_user_id IS NULL
            OR c.account_manager_user_id = :business_source_owner_user_id
          )
          AND (
            :search IS NULL
            OR c.name LIKE '%' + :search + '%'
            OR c.industry LIKE '%' + :search + '%'
          )
        )
        SELECT *
        FROM filtered_clients
        ORDER BY updated_at DESC, id DESC
        OFFSET :offset ROWS FETCH NEXT :page_size ROWS ONLY;
        """
    )
    with engine.connect() as connection:
      rows = connection.execute(
          query,
          {
              "location_id": filters.location_id,
              "status": filters.status,
              "client_owner_user_id": filters.client_owner_user_id,
              "business_source_owner_user_id": filters.business_source_owner_user_id,
              "search": filters.search,
              "offset": (filters.page - 1) * filters.page_size,
              "page_size": filters.page_size,
          },
      ).mappings().all()

    total = rows[0]["total_count"] if rows else 0
    return [_map_client(row) for row in rows], total


def _client_select_sql() -> str:
    return """
        SELECT
          c.id,
          c.branch_id AS location_id,
          CAST(NULL AS NVARCHAR(50)) AS client_code,
          c.name AS client_name,
          c.industry,
          c.status,
          c.account_manager_user_id AS business_source_owner_user_id,
          source_owner.full_name AS business_source_owner_name,
          c.account_manager_user_id AS client_owner_user_id,
          client_owner.full_name AS client_owner_name,
          c.placement_fee_pct,
          c.notes,
          CAST(NULL AS BIGINT) AS created_by_user_id,
          c.created_at,
          c.updated_at
        FROM dbo.client_companies AS c
        LEFT JOIN dbo.users AS source_owner
          ON source_owner.id = c.account_manager_user_id
        LEFT JOIN dbo.users AS client_owner
          ON client_owner.id = c.account_manager_user_id
    """


def find_client_by_id(engine: Engine, client_id: int) -> ClientRecord | None:
    query = text(f"{_client_select_sql()} WHERE c.id = :client_id;")
    with engine.connect() as connection:
        row = connection.execute(query, {"client_id": client_id}).mappings().first()
    return _map_client(row) if row else None


def find_client_by_code(engine: Engine, client_code: str) -> ClientRecord | None:
    query = text(f"{_client_select_sql()} WHERE c.name = :client_code;")
    with engine.connect() as connection:
        row = connection.execute(query, {"client_code": client_code}).mappings().first()
    return _map_client(row) if row else None


def create_client(engine: Engine, payload: ClientCreate) -> ClientRecord:
    query = text(
        """
        INSERT INTO dbo.client_companies (
          branch_id,
          name,
          relationship_type,
          industry,
          status,
          account_manager_user_id,
          notes,
          placement_fee_pct
        )
        OUTPUT INSERTED.id
        VALUES (
          :location_id,
          :client_name,
          N'direct-client',
          :industry,
          :status,
          :client_owner_user_id,
          :notes,
          :placement_fee_pct
        );
        """
    )
    with engine.begin() as connection:
        client_id = connection.execute(
            query,
            {
                "location_id": payload.location_id,
                "client_code": payload.client_code,
                "client_name": payload.client_name,
                "industry": payload.industry,
                "status": payload.status,
                "business_source_owner_user_id": payload.business_source_owner_user_id,
                "client_owner_user_id": payload.client_owner_user_id,
                "notes": payload.notes,
                "placement_fee_pct": payload.placement_fee_pct,
                "created_by_user_id": payload.created_by_user_id,
            },
        ).scalar_one()
    created = find_client_by_id(engine, int(client_id))
    if created is None:
        raise RuntimeError("Created client could not be reloaded")
    return created


def update_client(engine: Engine, client_id: int, payload: ClientUpdate) -> ClientRecord:
    query = text(
        """
        UPDATE dbo.client_companies
        SET
          name = COALESCE(:client_name, name),
          industry = CASE WHEN :has_industry = 1 THEN :industry ELSE industry END,
          account_manager_user_id = COALESCE(:client_owner_user_id, account_manager_user_id),
          status = COALESCE(:status, status),
          notes = CASE WHEN :has_notes = 1 THEN :notes ELSE notes END,
          placement_fee_pct = CASE WHEN :has_fee = 1 THEN :placement_fee_pct ELSE placement_fee_pct END,
          updated_at = SYSUTCDATETIME()
        WHERE id = :client_id;
        """
    )
    with engine.begin() as connection:
        connection.execute(
            query,
            {
                "client_id": client_id,
                "client_name": payload.client_name,
                "has_industry": 1 if "industry" in payload.model_fields_set else 0,
                "industry": payload.industry,
                "client_owner_user_id": payload.client_owner_user_id,
                "business_source_owner_user_id": payload.business_source_owner_user_id,
                "status": payload.status,
                "has_notes": 1 if "notes" in payload.model_fields_set else 0,
                "notes": payload.notes,
                "has_fee": 1 if "placement_fee_pct" in payload.model_fields_set else 0,
                "placement_fee_pct": payload.placement_fee_pct,
            },
        )
    updated = find_client_by_id(engine, client_id)
    if updated is None:
        raise RuntimeError("Updated client could not be reloaded")
    return updated


def list_client_contacts(engine: Engine, client_id: int) -> list[ClientContactRecord]:
    query = text(
        """
        SELECT
          id,
          client_company_id AS client_id,
          CAST(NULL AS BIGINT) AS location_id,
          full_name AS contact_name,
          designation,
          email,
          phone,
          is_primary AS is_primary_contact,
          CAST(0 AS BIT) AS is_secondary_contact,
          status,
          notes,
          CAST(NULL AS BIGINT) AS created_by_user_id,
          created_at,
          updated_at
        FROM dbo.client_contacts
        WHERE client_company_id = :client_id
        ORDER BY is_primary DESC, updated_at DESC, id DESC;
        """
    )
    with engine.connect() as connection:
        rows = connection.execute(query, {"client_id": client_id}).mappings().all()
    return [_map_client_contact(row) for row in rows]


def find_client_contact_by_id(engine: Engine, contact_id: int) -> ClientContactRecord | None:
    query = text(
        """
        SELECT TOP 1
          id,
          client_company_id AS client_id,
          CAST(NULL AS BIGINT) AS location_id,
          full_name AS contact_name,
          designation,
          email,
          phone,
          is_primary AS is_primary_contact,
          CAST(0 AS BIT) AS is_secondary_contact,
          status,
          notes,
          CAST(NULL AS BIGINT) AS created_by_user_id,
          created_at,
          updated_at
        FROM dbo.client_contacts
        WHERE id = :contact_id;
        """
    )
    with engine.connect() as connection:
        row = connection.execute(query, {"contact_id": contact_id}).mappings().first()
    return _map_client_contact(row) if row else None


def create_client_contact(engine: Engine, client_id: int, location_id: int, payload: ClientContactCreate) -> ClientContactRecord:
    query = text(
        """
        INSERT INTO dbo.client_contacts (
          client_company_id,
          full_name,
          designation,
          email,
          phone,
          is_primary,
          status,
          notes
        )
        OUTPUT INSERTED.id
        VALUES (
          :client_id,
          :contact_name,
          :designation,
          :email,
          :phone,
          :is_primary,
          :status,
          :notes
        );
        """
    )
    with engine.begin() as connection:
        contact_id = connection.execute(
            query,
            {
                "location_id": location_id,
                "client_id": client_id,
                "contact_name": payload.contact_name,
                "designation": payload.designation,
                "email": payload.email,
                "phone": payload.phone,
                "is_primary": 1 if payload.is_primary_contact else 0,
                "is_secondary": 1 if payload.is_secondary_contact else 0,
                "status": payload.status,
                "notes": payload.notes,
                "created_by_user_id": payload.created_by_user_id,
            },
        ).scalar_one()
    created = find_client_contact_by_id(engine, int(contact_id))
    if created is None:
        raise RuntimeError("Created client contact could not be reloaded")
    return created


def update_client_contact(engine: Engine, contact_id: int, payload: ClientContactUpdate) -> ClientContactRecord:
    query = text(
        """
        UPDATE dbo.client_contacts
        SET
          full_name = COALESCE(:contact_name, full_name),
          designation = CASE WHEN :has_designation = 1 THEN :designation ELSE designation END,
          email = CASE WHEN :has_email = 1 THEN :email ELSE email END,
          phone = CASE WHEN :has_phone = 1 THEN :phone ELSE phone END,
          is_primary = COALESCE(:is_primary, is_primary),
          status = COALESCE(:status, status),
          notes = CASE WHEN :has_notes = 1 THEN :notes ELSE notes END,
          updated_at = SYSUTCDATETIME()
        WHERE id = :contact_id;
        """
    )
    with engine.begin() as connection:
        connection.execute(
            query,
            {
                "contact_id": contact_id,
                "contact_name": payload.contact_name,
                "has_designation": 1 if "designation" in payload.model_fields_set else 0,
                "designation": payload.designation,
                "has_email": 1 if "email" in payload.model_fields_set else 0,
                "email": payload.email,
                "has_phone": 1 if "phone" in payload.model_fields_set else 0,
                "phone": payload.phone,
                "is_primary": payload.is_primary_contact,
                "is_secondary": payload.is_secondary_contact,
                "status": payload.status,
                "has_notes": 1 if "notes" in payload.model_fields_set else 0,
                "notes": payload.notes,
            },
        )
    updated = find_client_contact_by_id(engine, contact_id)
    if updated is None:
        raise RuntimeError("Updated client contact could not be reloaded")
    return updated
