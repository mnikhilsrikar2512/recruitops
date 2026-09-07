from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import Engine, text
from sqlalchemy.engine import RowMapping

from app.schemas.role import RoleCreate, RoleListFilters, RoleUpdate


@dataclass
class RoleRecord:
    id: int
    code: str
    name: str
    description: str | None
    is_system_role: bool
    status: str
    created_by_user_id: int | None
    created_at: object
    updated_at: object


def _map_role(row: RowMapping) -> RoleRecord:
    return RoleRecord(
        id=row["id"],
        code=row["code"],
        name=row["name"],
        description=row["description"],
        is_system_role=row["is_system_role"],
        status=row["status"],
        created_by_user_id=row["created_by_user_id"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def list_roles(engine: Engine, filters: RoleListFilters) -> tuple[list[RoleRecord], int]:
    query = text(
        """
        WITH filtered_roles AS (
          SELECT
            r.id,
            r.code,
            r.name,
            r.description,
            CAST(CASE WHEN r.code = N'admin' THEN 1 ELSE 0 END AS BIT) AS is_system_role,
            N'active' AS status,
            CAST(NULL AS BIGINT) AS created_by_user_id,
            r.created_at,
            r.updated_at,
            COUNT(*) OVER() AS total_count
          FROM dbo.roles AS r
          WHERE (
            :search IS NULL
            OR r.name LIKE '%' + :search + '%'
            OR r.code LIKE '%' + :search + '%'
          )
        )
        SELECT *
        FROM filtered_roles
        ORDER BY updated_at DESC, id DESC
        OFFSET :offset ROWS FETCH NEXT :page_size ROWS ONLY;
        """
    )

    with engine.connect() as connection:
        result = connection.execute(
            query,
            {
                "status": filters.status,
                "search": filters.search,
                "offset": (filters.page - 1) * filters.page_size,
                "page_size": filters.page_size,
            },
        )
        rows = result.mappings().all()

    total = rows[0]["total_count"] if rows else 0
    return [_map_role(row) for row in rows], total


def find_role_by_id(engine: Engine, role_id: int) -> RoleRecord | None:
    query = text(
        """
        SELECT TOP 1
          r.id,
          r.code,
          r.name,
          r.description,
          CAST(CASE WHEN r.code = N'admin' THEN 1 ELSE 0 END AS BIT) AS is_system_role,
          N'active' AS status,
          CAST(NULL AS BIGINT) AS created_by_user_id,
          r.created_at,
          r.updated_at
        FROM dbo.roles AS r
        WHERE r.id = :role_id;
        """
    )
    with engine.connect() as connection:
        row = connection.execute(query, {"role_id": role_id}).mappings().first()
    return _map_role(row) if row else None


def find_role_by_code(engine: Engine, code: str) -> RoleRecord | None:
    query = text(
        """
        SELECT TOP 1
          r.id,
          r.code,
          r.name,
          r.description,
          CAST(CASE WHEN r.code = N'admin' THEN 1 ELSE 0 END AS BIT) AS is_system_role,
          N'active' AS status,
          CAST(NULL AS BIGINT) AS created_by_user_id,
          r.created_at,
          r.updated_at
        FROM dbo.roles AS r
        WHERE r.code = :code;
        """
    )
    with engine.connect() as connection:
        row = connection.execute(query, {"code": code}).mappings().first()
    return _map_role(row) if row else None


def create_role(engine: Engine, payload: RoleCreate) -> RoleRecord | None:
    query = text(
        """
        INSERT INTO dbo.roles (
          code,
          name,
          description
        )
        OUTPUT INSERTED.id
        VALUES (
          :code,
          :name,
          :description
        );
        """
    )
    with engine.begin() as connection:
        row = connection.execute(
            query,
            {
                "code": payload.code,
                "name": payload.name,
                "description": payload.description,
            },
        ).mappings().first()
    return find_role_by_id(engine, int(row["id"])) if row else None


def update_role(engine: Engine, role_id: int, payload: RoleUpdate) -> RoleRecord | None:
    query = text(
        """
        UPDATE dbo.roles
        SET
          name = COALESCE(:name, name),
          description = CASE
            WHEN :has_description = 1 THEN :description
            ELSE description
          END,
          updated_at = SYSUTCDATETIME()
        OUTPUT INSERTED.id
        WHERE id = :role_id;
        """
    )
    with engine.begin() as connection:
        row = connection.execute(
            query,
            {
                "role_id": role_id,
                "name": payload.name,
                "has_description": 1 if "description" in payload.model_fields_set else 0,
                "description": payload.description,
                "status": payload.status,
            },
        ).mappings().first()
    return find_role_by_id(engine, role_id) if row else None


def list_permission_codes_for_role(engine: Engine, role_id: int) -> list[str]:
    query = text(
        """
        SELECT p.code
        FROM dbo.role_permissions AS rp
        INNER JOIN dbo.permissions AS p
          ON p.id = rp.permission_id
        WHERE rp.role_id = :role_id
        ORDER BY p.code;
        """
    )
    with engine.connect() as connection:
        rows = connection.execute(query, {"role_id": role_id}).mappings().all()
    return [row["code"] for row in rows]


def list_scope_rules_for_role(engine: Engine, role_id: int) -> dict[str, str]:
    _ = (engine, role_id)
    return {}


def count_permissions_by_codes(engine: Engine, permission_codes: list[str]) -> int:
    if not permission_codes:
        return 0

    bind_names = [f"code_{index}" for index in range(len(permission_codes))]
    placeholders = ", ".join(f":{name}" for name in bind_names)
    params = {name: permission_codes[index] for index, name in enumerate(bind_names)}
    query = text(
        f"""
        SELECT COUNT(*) AS total_count
        FROM dbo.permissions
        WHERE code IN ({placeholders});
        """
    )
    with engine.connect() as connection:
        row = connection.execute(query, params).mappings().first()
    return int(row["total_count"]) if row else 0


def replace_role_permissions(
    engine: Engine,
    role_id: int,
    permission_codes: list[str],
    scope_rules: dict[str, str],
) -> None:
    with engine.begin() as connection:
        connection.execute(
            text("DELETE FROM dbo.role_permissions WHERE role_id = :role_id;"),
            {"role_id": role_id},
        )

        if permission_codes:
            bind_names = [f"code_{index}" for index in range(len(permission_codes))]
            placeholders = ", ".join(f":{name}" for name in bind_names)
            params = {"role_id": role_id} | {
                name: permission_codes[index] for index, name in enumerate(bind_names)
            }
            connection.execute(
                text(
                    f"""
                    INSERT INTO dbo.role_permissions (role_id, permission_id)
                    SELECT
                      :role_id,
                      p.id
                    FROM dbo.permissions AS p
                    WHERE p.code IN ({placeholders});
                    """
                ),
                params,
            )

        _ = scope_rules

