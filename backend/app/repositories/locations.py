from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import Engine, text
from sqlalchemy.engine import RowMapping

from app.schemas.location import LocationCreate, LocationListFilters, LocationUpdate


@dataclass
class LocationRecord:
    id: int
    location_name: str
    location_code: str
    address: str | None
    status: str
    location_head_user_id: int | None
    location_head_name: str | None
    offers_enabled: bool | None = None
    created_at: object = None
    updated_at: object = None


def _map_location(row: RowMapping) -> LocationRecord:
    return LocationRecord(
        id=row["id"],
        location_name=row["location_name"],
        location_code=row["location_code"],
        address=row["address"],
        status=row["status"],
        location_head_user_id=row["location_head_user_id"],
        location_head_name=row["location_head_name"],
        offers_enabled=(None if row["offers_enabled"] is None else bool(row["offers_enabled"])),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def list_locations(engine: Engine, filters: LocationListFilters) -> tuple[list[LocationRecord], int]:
    query = text(
        """
        WITH filtered_locations AS (
          SELECT
            l.id,
            l.name AS location_name,
            l.code AS location_code,
            l.address,
            l.status,
            l.manager_user_id AS location_head_user_id,
            u.full_name AS location_head_name,
            l.offers_enabled,
            l.created_at,
            l.updated_at
          FROM dbo.branches AS l
          LEFT JOIN dbo.users AS u
            ON u.id = l.manager_user_id
          WHERE (:status IS NULL OR l.status = :status)
          AND (:tenant_id IS NULL OR l.tenant_id = :tenant_id)
          AND (
            :search IS NULL
            OR l.name LIKE '%' + :search + '%'
            OR l.code LIKE '%' + :search + '%'
            OR l.location LIKE '%' + :search + '%'
          )
        )
        SELECT
          *,
          COUNT(*) OVER() AS total_count
        FROM filtered_locations
        ORDER BY updated_at DESC, id DESC
        OFFSET :offset ROWS FETCH NEXT :page_size ROWS ONLY;
        """
    )

    with engine.connect() as connection:
        result = connection.execute(
            query,
            {
                "status": filters.status,
                "tenant_id": filters.tenant_id,
                "search": filters.search,
                "offset": (filters.page - 1) * filters.page_size,
                "page_size": filters.page_size,
            },
        )
        rows = result.mappings().all()

    total = rows[0]["total_count"] if rows else 0
    return [_map_location(row) for row in rows], total


def find_location_by_id(engine: Engine, location_id: int) -> LocationRecord | None:
    query = text(
        """
        SELECT TOP 1
          l.id,
          l.name AS location_name,
          l.code AS location_code,
          l.address,
          l.status,
          l.manager_user_id AS location_head_user_id,
          u.full_name AS location_head_name,
          l.offers_enabled,
          l.created_at,
          l.updated_at
        FROM dbo.branches AS l
        LEFT JOIN dbo.users AS u
          ON u.id = l.manager_user_id
        WHERE l.id = :location_id;
        """
    )

    with engine.connect() as connection:
        row = connection.execute(query, {"location_id": location_id}).mappings().first()

    return _map_location(row) if row else None


def find_location_by_code(engine: Engine, location_code: str, tenant_id: int | None = None) -> LocationRecord | None:
    """Office codes are unique per company (010_tenants)."""
    query = text(
        """
        SELECT TOP 1
          l.id,
          l.name AS location_name,
          l.code AS location_code,
          l.address,
          l.status,
          l.manager_user_id AS location_head_user_id,
          u.full_name AS location_head_name,
          l.offers_enabled,
          l.created_at,
          l.updated_at
        FROM dbo.branches AS l
        LEFT JOIN dbo.users AS u
          ON u.id = l.manager_user_id
        WHERE l.code = :location_code
          AND (:tenant_id IS NULL OR l.tenant_id = :tenant_id);
        """
    )

    with engine.connect() as connection:
        row = connection.execute(query, {"location_code": location_code, "tenant_id": tenant_id}).mappings().first()

    return _map_location(row) if row else None


def user_exists(engine: Engine, user_id: int) -> bool:
    query = text(
        """
        SELECT TOP 1 1 AS found_value
        FROM dbo.users
        WHERE id = :user_id;
        """
    )

    with engine.connect() as connection:
        row = connection.execute(query, {"user_id": user_id}).first()

    return row is not None


def create_location(engine: Engine, payload: LocationCreate, tenant_id: int | None = None) -> LocationRecord:
    # tenant_id None only in legacy/unit contexts: fall back to the default company.
    query = text(
        """
        INSERT INTO dbo.branches (
          name,
          code,
          location,
          address,
          status,
          manager_user_id,
          offers_enabled,
          tenant_id
        )
        OUTPUT INSERTED.id
        VALUES (
          :location_name,
          :location_code,
          :location_value,
          :address,
          :status,
          :location_head_user_id,
          CASE WHEN :has_offers_enabled = 1 THEN :offers_enabled ELSE 1 END,
          COALESCE(:tenant_id, (SELECT t.id FROM dbo.tenants AS t WHERE t.slug = N'default'))
        );
        """
    )
    # dbo.branches and dbo.locations are parallel tables and the code assumes
    # branch id == location id (several FKs point at dbo.locations), so every
    # new office is mirrored with the same id.
    mirror_query = text(
        """
        IF NOT EXISTS (SELECT 1 FROM dbo.locations WHERE id = :id)
        BEGIN
          SET IDENTITY_INSERT dbo.locations ON;
          INSERT INTO dbo.locations (id, name, code, location, address, status, location_head_user_id, tenant_id)
          SELECT b.id, b.name, b.code, b.location, b.address, b.status, b.manager_user_id, b.tenant_id
          FROM dbo.branches AS b WHERE b.id = :id;
          SET IDENTITY_INSERT dbo.locations OFF;
        END
        """
    )

    with engine.begin() as connection:
        result = connection.execute(
            query,
            {
                "location_name": payload.location_name,
                "location_code": payload.location_code,
                "location_value": payload.location_name,
                "address": payload.address,              "status": payload.status,
              "location_head_user_id": payload.location_head_user_id,
              "has_offers_enabled": 1 if "offers_enabled" in payload.model_fields_set else 0,
              "offers_enabled": payload.offers_enabled,
              "tenant_id": tenant_id,
            },
        )
        location_id = result.scalar_one()
        connection.execute(mirror_query, {"id": int(location_id)})

    created = find_location_by_id(engine, int(location_id))
    if created is None:
        raise RuntimeError("Created location could not be reloaded")
    return created


def update_location(engine: Engine, location_id: int, payload: LocationUpdate) -> LocationRecord:
    query = text(
        """
        UPDATE dbo.branches
        SET
          name = COALESCE(:location_name, name),
          location = COALESCE(:location_name, location),
          address = CASE
            WHEN :has_address = 1 THEN :address
            ELSE address
          END,
          status = COALESCE(:status, status),
          manager_user_id = CASE
            WHEN :has_location_head_user_id = 1 THEN :location_head_user_id
            ELSE manager_user_id
          END,
          offers_enabled = CASE
            WHEN :has_offers_enabled = 1 THEN :offers_enabled
            ELSE offers_enabled
          END,
          updated_at = SYSUTCDATETIME()
        WHERE id = :location_id;
        """
    )

    with engine.begin() as connection:
        connection.execute(
            query,
            {
                "location_id": location_id,
                "location_name": payload.location_name,
                "has_address": 1 if "address" in payload.model_fields_set else 0,
                "address": payload.address,
                "status": payload.status,
                "has_location_head_user_id": 1 if "location_head_user_id" in payload.model_fields_set else 0,
                "location_head_user_id": payload.location_head_user_id,
                "has_offers_enabled": 1 if "offers_enabled" in payload.model_fields_set else 0,
                "offers_enabled": payload.offers_enabled,
            },
        )
        # keep the dbo.locations mirror in step (same id)
        connection.execute(
            text(
                """
                UPDATE l SET l.name = b.name, l.location = b.location, l.address = b.address,
                       l.status = b.status, l.location_head_user_id = b.manager_user_id,
                       l.updated_at = SYSUTCDATETIME()
                FROM dbo.locations AS l INNER JOIN dbo.branches AS b ON b.id = l.id
                WHERE l.id = :location_id;
                """
            ),
            {"location_id": location_id},
        )

    updated = find_location_by_id(engine, location_id)
    if updated is None:
        raise RuntimeError("Updated location could not be reloaded")
    return updated
