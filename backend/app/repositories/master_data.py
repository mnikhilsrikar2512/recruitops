from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import Engine, text
from sqlalchemy.engine import RowMapping

from app.schemas.master_data import MasterDataValueCreate, MasterDataValueUpdate


@dataclass
class MasterDataCategoryRecord:
    id: int
    code: str
    name: str
    description: str | None
    is_system: bool
    created_at: object
    updated_at: object


@dataclass
class MasterDataValueRecord:
    id: int
    category_id: int
    code: str
    name: str
    description: str | None
    sort_order: int
    is_active: bool
    created_at: object
    updated_at: object
    tenant_id: int | None = None


def _map_category(row: RowMapping) -> MasterDataCategoryRecord:
    return MasterDataCategoryRecord(
        id=row["id"],
        code=row["code"],
        name=row["name"],
        description=row["description"],
        is_system=row["is_system"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _map_value(row: RowMapping) -> MasterDataValueRecord:
    return MasterDataValueRecord(
        id=row["id"],
        category_id=row["category_id"],
        code=row["code"],
        name=row["name"],
        description=row["description"],
        sort_order=row["sort_order"],
        is_active=row["is_active"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        tenant_id=row.get("tenant_id"),
    )


def find_category_by_code(engine: Engine, category_code: str) -> MasterDataCategoryRecord | None:
    query = text(
        """
        SELECT TOP 1 id, code, name, description, is_system, created_at, updated_at
        FROM dbo.master_data_categories
        WHERE code = :category_code;
        """
    )
    with engine.connect() as connection:
        row = connection.execute(query, {"category_code": category_code}).mappings().first()
    return _map_category(row) if row else None


def find_category_by_id(engine: Engine, category_id: int) -> MasterDataCategoryRecord | None:
    query = text(
        """
        SELECT TOP 1 id, code, name, description, is_system, created_at, updated_at
        FROM dbo.master_data_categories
        WHERE id = :category_id;
        """
    )
    with engine.connect() as connection:
        row = connection.execute(query, {"category_id": category_id}).mappings().first()
    return _map_category(row) if row else None


def list_values_by_category(
    engine: Engine,
    category_id: int,
    page: int = 1,
    page_size: int = 50,
    tenant_id: int | None = None,
) -> tuple[list[MasterDataValueRecord], int]:
    """A company's own values (tenant_id); templates when tenant_id is None."""
    query = text(
        """
        WITH filtered AS (
          SELECT id, category_id, code, name, description, sort_order, is_active,
                 created_at, updated_at, tenant_id
          FROM dbo.master_data_values
          WHERE category_id = :category_id
          AND ((:tenant_id IS NULL AND tenant_id IS NULL) OR tenant_id = :tenant_id)
        )
        SELECT *, COUNT(*) OVER() AS total_count
        FROM filtered
        ORDER BY sort_order ASC, name ASC
        OFFSET :offset ROWS FETCH NEXT :page_size ROWS ONLY;
        """
    )
    with engine.connect() as connection:
        rows = connection.execute(
            query,
            {
                "category_id": category_id,
                "tenant_id": tenant_id,
                "offset": (page - 1) * page_size,
                "page_size": page_size,
            },
        ).mappings().all()
    total = rows[0]["total_count"] if rows else 0
    return [_map_value(row) for row in rows], total


def find_value_by_code(
    engine: Engine, category_id: int, code: str, tenant_id: int | None = None
) -> MasterDataValueRecord | None:
    query = text(
        """
        SELECT TOP 1 id, category_id, code, name, description, sort_order, is_active,
               created_at, updated_at, tenant_id
        FROM dbo.master_data_values
        WHERE category_id = :category_id AND code = :code
        AND ((:tenant_id IS NULL AND tenant_id IS NULL) OR tenant_id = :tenant_id);
        """
    )
    with engine.connect() as connection:
        row = connection.execute(
            query, {"category_id": category_id, "code": code, "tenant_id": tenant_id}
        ).mappings().first()
    return _map_value(row) if row else None


def find_value_by_id(engine: Engine, value_id: int) -> MasterDataValueRecord | None:
    query = text(
        """
        SELECT TOP 1 id, category_id, code, name, description, sort_order, is_active,
               created_at, updated_at, tenant_id
        FROM dbo.master_data_values
        WHERE id = :value_id;
        """
    )
    with engine.connect() as connection:
        row = connection.execute(query, {"value_id": value_id}).mappings().first()
    return _map_value(row) if row else None


def create_value(
    engine: Engine, category_id: int, payload: MasterDataValueCreate, tenant_id: int | None = None
) -> MasterDataValueRecord:
    query = text(
        """
        INSERT INTO dbo.master_data_values (category_id, code, name, description, sort_order, is_active, tenant_id)
        OUTPUT INSERTED.id
        VALUES (:category_id, :code, :name, :description, :sort_order, :is_active, :tenant_id);
        """
    )
    with engine.begin() as connection:
        result = connection.execute(
            query,
            {
                "category_id": category_id,
                "code": payload.code,
                "name": payload.name,
                "description": payload.description,
                "sort_order": payload.sort_order,
                "is_active": payload.is_active,
                "tenant_id": tenant_id,
            },
        )
        value_id = result.scalar_one()

    created = find_value_by_id(engine, int(value_id))
    if created is None:
        raise RuntimeError("Created master data value could not be reloaded")
    return created


def update_value(
    engine: Engine,
    value_id: int,
    payload: MasterDataValueUpdate,
) -> MasterDataValueRecord:
    query = text(
        """
        UPDATE dbo.master_data_values
        SET
          name = COALESCE(:name, name),
          description = CASE
            WHEN :has_description = 1 THEN :description
            ELSE description
          END,
          sort_order = COALESCE(:sort_order, sort_order),
          is_active = CASE
            WHEN :has_is_active = 1 THEN :is_active
            ELSE is_active
          END,
          updated_at = SYSUTCDATETIME()
        WHERE id = :value_id;
        """
    )
    with engine.begin() as connection:
        connection.execute(
            query,
            {
                "value_id": value_id,
                "name": payload.name,
                "description": payload.description,
                "has_description": 1 if "description" in payload.model_fields_set else 0,
                "sort_order": payload.sort_order,
                "is_active": payload.is_active,
                "has_is_active": 1 if "is_active" in payload.model_fields_set else 0,
            },
        )

    updated = find_value_by_id(engine, value_id)
    if updated is None:
        raise RuntimeError("Updated master data value could not be reloaded")
    return updated


def copy_templates_for_tenant(engine: Engine, category_id: int, tenant_id: int) -> None:
    """First time a company opens a list it gets its own copy of the shared
    templates (tenant_id NULL), which it can then edit freely."""
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                IF NOT EXISTS (SELECT 1 FROM dbo.master_data_values WHERE category_id = :category_id AND tenant_id = :tenant_id)
                    INSERT INTO dbo.master_data_values (
                        category_id, code, name, description, sort_order, parent_value_id, is_active,
                        numeric_value_int, numeric_value_decimal, text_value, metadata_json, tenant_id
                    )
                    SELECT category_id, code, name, description, sort_order, NULL, is_active,
                           numeric_value_int, numeric_value_decimal, text_value, metadata_json, :tenant_id
                    FROM dbo.master_data_values
                    WHERE category_id = :category_id AND tenant_id IS NULL;
                """
            ),
            {"category_id": category_id, "tenant_id": tenant_id},
        )
