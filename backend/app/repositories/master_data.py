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
) -> tuple[list[MasterDataValueRecord], int]:
    query = text(
        """
        WITH filtered AS (
          SELECT id, category_id, code, name, description, sort_order, is_active,
                 created_at, updated_at
          FROM dbo.master_data_values
          WHERE category_id = :category_id
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
                "offset": (page - 1) * page_size,
                "page_size": page_size,
            },
        ).mappings().all()
    total = rows[0]["total_count"] if rows else 0
    return [_map_value(row) for row in rows], total


def find_value_by_code(engine: Engine, category_id: int, code: str) -> MasterDataValueRecord | None:
    query = text(
        """
        SELECT TOP 1 id, category_id, code, name, description, sort_order, is_active,
               created_at, updated_at
        FROM dbo.master_data_values
        WHERE category_id = :category_id AND code = :code;
        """
    )
    with engine.connect() as connection:
        row = connection.execute(query, {"category_id": category_id, "code": code}).mappings().first()
    return _map_value(row) if row else None


def find_value_by_id(engine: Engine, value_id: int) -> MasterDataValueRecord | None:
    query = text(
        """
        SELECT TOP 1 id, category_id, code, name, description, sort_order, is_active,
               created_at, updated_at
        FROM dbo.master_data_values
        WHERE id = :value_id;
        """
    )
    with engine.connect() as connection:
        row = connection.execute(query, {"value_id": value_id}).mappings().first()
    return _map_value(row) if row else None


def create_value(engine: Engine, category_id: int, payload: MasterDataValueCreate) -> MasterDataValueRecord:
    query = text(
        """
        INSERT INTO dbo.master_data_values (category_id, code, name, description, sort_order, is_active)
        OUTPUT INSERTED.id
        VALUES (:category_id, :code, :name, :description, :sort_order, :is_active);
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
