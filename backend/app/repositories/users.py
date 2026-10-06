from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import Engine, text
from sqlalchemy.engine import RowMapping

from app.schemas.user import UserCreate, UserListFilters, UserUpdate


@dataclass
class UserRecord:
    id: int
    full_name: str
    email: str
    phone: str | None
    employee_code: str | None
    status: str
    business_title: str | None
    primary_location_id: int | None
    primary_location_name: str | None
    primary_role_id: int
    primary_role_name: str
    primary_role_code: str | None
    reporting_manager_user_id: int | None
    reporting_manager_name: str | None
    password_setup_status: str
    force_password_change_on_first_login: bool
    created_at: object
    updated_at: object


def _map_user(row: RowMapping) -> UserRecord:
    return UserRecord(
        id=row["id"],
        full_name=row["full_name"],
        email=row["email"],
        phone=row["phone"],
        employee_code=row["employee_code"],
        status=row["status"],
        business_title=row["business_title"],
        primary_location_id=row["primary_location_id"],
        primary_location_name=row["primary_location_name"],
        primary_role_id=row["primary_role_id"],
        primary_role_name=row["primary_role_name"],
        primary_role_code=row.get("primary_role_code"),
        reporting_manager_user_id=row["reporting_manager_user_id"],
        reporting_manager_name=row["reporting_manager_name"],
        password_setup_status=row["password_setup_status"],
        force_password_change_on_first_login=row["force_password_change_on_first_login"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _user_select_sql() -> str:
    return """
        SELECT
          u.id,
          u.full_name,
          u.email,
          u.phone,
          u.employee_code,
          u.status,
          u.business_title,
          ubr.branch_id AS primary_location_id,
          b.name AS primary_location_name,
          u.default_role_id AS primary_role_id,
          r.name AS primary_role_name,
          r.code AS primary_role_code,
          u.reporting_manager_user_id,
          manager.full_name AS reporting_manager_name,
          u.password_setup_status,
          u.force_password_change_on_first_login,
          u.created_at,
          u.updated_at
        FROM dbo.users AS u
        INNER JOIN dbo.roles AS r
          ON r.id = u.default_role_id
        LEFT JOIN dbo.user_branch_roles AS ubr
          ON ubr.user_id = u.id
         AND ubr.is_primary = 1
         AND ubr.status = N'active'
        LEFT JOIN dbo.branches AS b
          ON b.id = ubr.branch_id
        LEFT JOIN dbo.users AS manager
          ON manager.id = u.reporting_manager_user_id
    """


def list_users(engine: Engine, filters: UserListFilters) -> tuple[list[UserRecord], int]:
    query = text(
        f"""
        WITH filtered_users AS (
          {_user_select_sql()}
          WHERE (:location_id IS NULL OR ubr.branch_id = :location_id)
          AND (:tenant_id IS NULL OR u.tenant_id = :tenant_id)
          AND (:role_id IS NULL OR u.default_role_id = :role_id)
          AND (:status IS NULL OR u.status = :status)
          AND (
            :search IS NULL
            OR u.full_name LIKE '%' + :search + '%'
            OR u.email LIKE '%' + :search + '%'
            OR u.employee_code LIKE '%' + :search + '%'
          )
        )
        SELECT
          *,
          COUNT(*) OVER() AS total_count
        FROM filtered_users
        ORDER BY updated_at DESC, id DESC
        OFFSET :offset ROWS FETCH NEXT :page_size ROWS ONLY;
        """
    )
    with engine.connect() as connection:
        rows = connection.execute(
            query,
            {
                "location_id": filters.location_id,
                "tenant_id": filters.tenant_id,
                "role_id": filters.role_id,
                "status": filters.status,
                "search": filters.search,
                "offset": (filters.page - 1) * filters.page_size,
                "page_size": filters.page_size,
            },
        ).mappings().all()
    total = rows[0]["total_count"] if rows else 0
    return [_map_user(row) for row in rows], total


def find_user_by_id(engine: Engine, user_id: int) -> UserRecord | None:
    query = text(
        f"""
        SELECT TOP 1 *
        FROM (
          {_user_select_sql()}
        ) AS selected_users
        WHERE id = :user_id;
        """
    )
    with engine.connect() as connection:
        row = connection.execute(query, {"user_id": user_id}).mappings().first()
    return _map_user(row) if row else None


def find_user_by_email(engine: Engine, email: str) -> UserRecord | None:
    query = text(
        f"""
        SELECT TOP 1 *
        FROM (
          {_user_select_sql()}
        ) AS selected_users
        WHERE LOWER(email) = LOWER(:email);
        """
    )
    with engine.connect() as connection:
        row = connection.execute(query, {"email": email}).mappings().first()
    return _map_user(row) if row else None


def find_user_by_employee_code(engine: Engine, employee_code: str) -> UserRecord | None:
    query = text(
        f"""
        SELECT TOP 1 *
        FROM (
          {_user_select_sql()}
        ) AS selected_users
        WHERE employee_code = :employee_code;
        """
    )
    with engine.connect() as connection:
        row = connection.execute(query, {"employee_code": employee_code}).mappings().first()
    return _map_user(row) if row else None


def location_exists(engine: Engine, location_id: int) -> bool:
    query = text("SELECT TOP 1 1 AS found_value FROM dbo.branches WHERE id = :location_id;")
    with engine.connect() as connection:
        row = connection.execute(query, {"location_id": location_id}).first()
    return row is not None


def role_exists(engine: Engine, role_id: int) -> bool:
    query = text("SELECT TOP 1 1 AS found_value FROM dbo.roles WHERE id = :role_id;")
    with engine.connect() as connection:
        row = connection.execute(query, {"role_id": role_id}).first()
    return row is not None


def count_active_admins(engine: Engine, same_company_as_user_id: int | None = None) -> int:
    """Number of active users holding the fixed admin role — within the
    company of ``same_company_as_user_id`` when given (each company must
    keep at least one admin)."""
    query = text(
        """
        SELECT COUNT(*) AS admin_count
        FROM dbo.users AS u
        INNER JOIN dbo.roles AS r ON r.id = u.default_role_id
        WHERE r.code = N'admin' AND u.status = N'active'
          AND (:user_id IS NULL OR u.tenant_id = (SELECT su.tenant_id FROM dbo.users AS su WHERE su.id = :user_id));
        """
    )
    with engine.connect() as connection:
        return int(connection.execute(query, {"user_id": same_company_as_user_id}).scalar_one())


def count_user_active_requisitions(engine: Engine, user_id: int) -> int:
    query = text(
        """
        SELECT COUNT(*) AS total_count
        FROM dbo.requisitions
        WHERE status IN (N'draft', N'open', N'on-hold')
        AND owner_user_id = :user_id;
        """
    )
    with engine.connect() as connection:
        return int(connection.execute(query, {"user_id": user_id}).scalar_one())


def count_user_active_assignments(engine: Engine, user_id: int) -> int:
    query = text(
        """
        SELECT COUNT(*) AS total_count
        FROM dbo.requisition_assignments
        WHERE assigned_user_id = :user_id
        AND status = N'active';
        """
    )
    with engine.connect() as connection:
        return int(connection.execute(query, {"user_id": user_id}).scalar_one())


def count_user_active_candidate_ownership(engine: Engine, user_id: int) -> int:
    query = text(
        """
        SELECT COUNT(*) AS total_count
        FROM dbo.candidates
        WHERE primary_owner_user_id = :user_id
        AND profile_status IN (N'draft', N'active');
        """
    )
    with engine.connect() as connection:
        return int(connection.execute(query, {"user_id": user_id}).scalar_one())


def count_user_active_pipeline_ownership(engine: Engine, user_id: int) -> int:
    query = text(
        """
        SELECT COUNT(*) AS total_count
        FROM dbo.candidate_applications
        WHERE owner_user_id = :user_id
        AND application_status = N'active';
        """
    )
    with engine.connect() as connection:
        return int(connection.execute(query, {"user_id": user_id}).scalar_one())


def create_user(engine: Engine, payload: UserCreate, password_hash: str) -> UserRecord:
    insert_user_sql = text(
        """
        INSERT INTO dbo.users (
          employee_code,
          full_name,
          email,
          phone,
          password_hash,
          password_setup_status,
          force_password_change_on_first_login,
          status,
          default_role_id,
          hierarchy_level,
          reporting_manager_user_id,
          tenant_id
        )
        OUTPUT INSERTED.id
        VALUES (
          :employee_code,
          :full_name,
          :email,
          :phone,
          :password_hash,
          N'invited',
          1,
          :status,
          :primary_role_id,
          :hierarchy_level,
          :reporting_manager_user_id,
          (SELECT b.tenant_id FROM dbo.branches AS b WHERE b.id = :primary_location_id)
        );
        """
    )
    insert_location_role_sql = text(
        """
        INSERT INTO dbo.user_branch_roles (
          user_id,
          branch_id,
          role_id,
          is_primary,
          status,
          start_date
        )
        VALUES (
          :user_id,
          :location_id,
          :role_id,
          1,
          N'active',
          CAST(SYSUTCDATETIME() AS DATE)
        );
        """
    )
    with engine.begin() as connection:
        user_id = connection.execute(
            insert_user_sql,
            {
                "employee_code": payload.employee_code,
                "full_name": payload.full_name,
                "email": str(payload.email),
                "phone": payload.phone,
                "password_hash": password_hash,
                "status": payload.status,
                "primary_role_id": payload.primary_role_id,
                "hierarchy_level": "recruiter",
                "reporting_manager_user_id": payload.reporting_manager_user_id,
                "primary_location_id": payload.primary_location_id,
            },
        ).scalar_one()
        connection.execute(
            insert_location_role_sql,
            {
                "user_id": int(user_id),
                "location_id": payload.primary_location_id,
                "role_id": payload.primary_role_id,
            },
        )
    created = find_user_by_id(engine, int(user_id))
    if created is None:
        raise RuntimeError("Created user could not be reloaded")
    return created


def update_own_profile_fields(
    engine: Engine,
    user_id: int,
    *,
    full_name: str | None = None,
    phone: str | None = None,
    has_full_name: bool = False,
    has_phone: bool = False,
) -> None:
    """Self-service profile write: only full_name and/or phone.

    Decoupled from admin ``update_user`` so role/location/status side effects
    cannot accidentally fire from ProfileUpdateRequest growth.
    """
    if not has_full_name and not has_phone:
        return
    update_sql = text(
        """
        UPDATE dbo.users
        SET
          full_name = CASE WHEN :has_full_name = 1 THEN :full_name ELSE full_name END,
          phone = CASE WHEN :has_phone = 1 THEN :phone ELSE phone END,
          updated_at = SYSUTCDATETIME()
        WHERE id = :user_id;
        """
    )
    with engine.begin() as connection:
        connection.execute(
            update_sql,
            {
                "user_id": user_id,
                "has_full_name": 1 if has_full_name else 0,
                "full_name": full_name,
                "has_phone": 1 if has_phone else 0,
                "phone": phone,
            },
        )


def update_user(engine: Engine, user_id: int, payload: UserUpdate, before: UserRecord) -> UserRecord:
    update_sql = text(
        """
        UPDATE dbo.users
        SET
          full_name = COALESCE(:full_name, full_name),
          phone = CASE WHEN :has_phone = 1 THEN :phone ELSE phone END,
          business_title = CASE WHEN :has_business_title = 1 THEN :business_title ELSE business_title END,
          default_role_id = COALESCE(:primary_role_id, default_role_id),
          reporting_manager_user_id = CASE
            WHEN :has_reporting_manager_user_id = 1 THEN :reporting_manager_user_id
            ELSE reporting_manager_user_id
          END,
          status = COALESCE(:status, status),
          updated_at = SYSUTCDATETIME()
        WHERE id = :user_id;
        """
    )
    deactivate_primary_role_sql = text(
        """
        UPDATE dbo.user_branch_roles
        SET
          status = N'inactive',
          is_primary = 0,
          updated_at = SYSUTCDATETIME(),
          end_date = CAST(SYSUTCDATETIME() AS DATE)
        WHERE user_id = :user_id
        AND is_primary = 1
        AND status = N'active';
        """
    )
    insert_primary_role_sql = text(
        """
        INSERT INTO dbo.user_branch_roles (
          user_id,
          branch_id,
          role_id,
          is_primary,
          status,
          start_date
        )
        VALUES (
          :user_id,
          :location_id,
          :role_id,
          1,
          N'active',
          CAST(SYSUTCDATETIME() AS DATE)
        );
        """
    )
    with engine.begin() as connection:
        connection.execute(
            update_sql,
            {
                "user_id": user_id,
                "full_name": payload.full_name,
                "has_phone": 1 if "phone" in payload.model_fields_set else 0,
                "phone": payload.phone,
                "location_id": payload.primary_location_id,
                "primary_role_id": payload.primary_role_id,
                "has_reporting_manager_user_id": 1 if "reporting_manager_user_id" in payload.model_fields_set else 0,
                "reporting_manager_user_id": payload.reporting_manager_user_id,
                "has_business_title": 1 if "business_title" in payload.model_fields_set else 0,
                "business_title": payload.business_title,
                "status": payload.status,
            },
        )

        next_location_id = payload.primary_location_id or before.primary_location_id
        next_role_id = payload.primary_role_id or before.primary_role_id
        location_changed = next_location_id != before.primary_location_id
        role_changed = next_role_id != before.primary_role_id

        if next_location_id and next_role_id and (location_changed or role_changed):
            connection.execute(deactivate_primary_role_sql, {"user_id": user_id})
            connection.execute(
                insert_primary_role_sql,
                {
                    "user_id": user_id,
                    "location_id": next_location_id,
                    "role_id": next_role_id,
                },
            )

    updated = find_user_by_id(engine, user_id)
    if updated is None:
        raise RuntimeError("Updated user could not be reloaded")
    return updated


def transfer_active_user_work_and_deactivate(
    engine: Engine,
    *,
    user_id: int,
    transfer_to_user_id: int | None,
) -> UserRecord:
    with engine.begin() as connection:
        if transfer_to_user_id is not None:
            connection.execute(
                text(
                    """
                    UPDATE dbo.requisitions
                    SET
                      owner_user_id = :transfer_to_user_id,
                      updated_at = SYSUTCDATETIME()
                    WHERE owner_user_id = :user_id;
                    """
                ),
                {"user_id": user_id, "transfer_to_user_id": transfer_to_user_id},
            )
            connection.execute(
                text(
                    """
                    UPDATE dbo.candidates
                    SET
                      primary_owner_user_id = :transfer_to_user_id,
                      updated_at = SYSUTCDATETIME()
                    WHERE primary_owner_user_id = :user_id
                    AND profile_status IN (N'draft', N'active');
                    """
                ),
                {"user_id": user_id, "transfer_to_user_id": transfer_to_user_id},
            )
            connection.execute(
                text(
                    """
                    UPDATE dbo.candidate_applications
                    SET
                      owner_user_id = :transfer_to_user_id,
                      updated_at = SYSUTCDATETIME()
                    WHERE owner_user_id = :user_id
                    AND application_status = N'active';
                    """
                ),
                {"user_id": user_id, "transfer_to_user_id": transfer_to_user_id},
            )

        connection.execute(
            text(
                """
                UPDATE dbo.users
                SET
                  status = N'inactive',
                  updated_at = SYSUTCDATETIME()
                WHERE id = :user_id;
                """
            ),
            {"user_id": user_id},
        )
        connection.execute(
            text(
                """
                UPDATE dbo.user_branch_roles
                SET
                  status = N'inactive',
                  is_primary = 0,
                  updated_at = SYSUTCDATETIME(),
                  end_date = CAST(SYSUTCDATETIME() AS DATE)
                WHERE user_id = :user_id
                AND is_primary = 1
                AND status = N'active';
                """
            ),
            {"user_id": user_id},
        )

    updated = find_user_by_id(engine, user_id)
    if updated is None:
        raise RuntimeError("Deactivated user could not be reloaded")
    return updated


def transfer_active_user_work_and_move(
    engine: Engine,
    *,
    user_id: int,
    transfer_to_user_id: int | None,
    new_primary_location_id: int,
    new_primary_role_id: int,
) -> UserRecord:
    deactivate_primary_role_sql = text(
        """
        UPDATE dbo.user_branch_roles
        SET
          status = N'inactive',
          is_primary = 0,
          updated_at = SYSUTCDATETIME(),
          end_date = CAST(SYSUTCDATETIME() AS DATE)
        WHERE user_id = :user_id
        AND is_primary = 1
        AND status = N'active';
        """
    )
    insert_primary_role_sql = text(
        """
        INSERT INTO dbo.user_branch_roles (
          user_id,
          branch_id,
          role_id,
          is_primary,
          status,
          start_date
        )
        VALUES (
          :user_id,
          :location_id,
          :role_id,
          1,
          N'active',
          CAST(SYSUTCDATETIME() AS DATE)
        );
        """
    )
    with engine.begin() as connection:
        if transfer_to_user_id is not None:
            connection.execute(
                text(
                    """
                    UPDATE dbo.requisitions
                    SET
                      owner_user_id = :transfer_to_user_id,
                      updated_at = SYSUTCDATETIME()
                    WHERE owner_user_id = :user_id;
                    """
                ),
                {"user_id": user_id, "transfer_to_user_id": transfer_to_user_id},
            )
            connection.execute(
                text(
                    """
                    UPDATE dbo.candidates
                    SET
                      primary_owner_user_id = :transfer_to_user_id,
                      updated_at = SYSUTCDATETIME()
                    WHERE primary_owner_user_id = :user_id
                    AND profile_status IN (N'draft', N'active');
                    """
                ),
                {"user_id": user_id, "transfer_to_user_id": transfer_to_user_id},
            )
            connection.execute(
                text(
                    """
                    UPDATE dbo.candidate_applications
                    SET
                      owner_user_id = :transfer_to_user_id,
                      updated_at = SYSUTCDATETIME()
                    WHERE owner_user_id = :user_id
                    AND application_status = N'active';
                    """
                ),
                {"user_id": user_id, "transfer_to_user_id": transfer_to_user_id},
            )

        connection.execute(
            text(
                """
                UPDATE dbo.users
                SET
                  default_role_id = :new_primary_role_id,
                  updated_at = SYSUTCDATETIME()
                WHERE id = :user_id;
                """
            ),
            {
                "user_id": user_id,
                "new_primary_location_id": new_primary_location_id,
                "new_primary_role_id": new_primary_role_id,
            },
        )
        connection.execute(deactivate_primary_role_sql, {"user_id": user_id})
        connection.execute(
            insert_primary_role_sql,
            {
                "user_id": user_id,
                "location_id": new_primary_location_id,
                "role_id": new_primary_role_id,
            },
        )

    updated = find_user_by_id(engine, user_id)
    if updated is None:
        raise RuntimeError("Moved user could not be reloaded")
    return updated


def update_user_password_hash(engine: Engine, user_id: int, password_hash: str) -> None:
    """Re-hash in place, preserving password_setup_status and force-change flags."""
    query = text(
        """
        UPDATE dbo.users
        SET
          password_hash = :password_hash,
          updated_at = SYSUTCDATETIME()
        WHERE id = :user_id;
        """
    )
    with engine.begin() as connection:
        connection.execute(query, {"user_id": user_id, "password_hash": password_hash})


def update_user_password_state(
    engine: Engine,
    user_id: int,
    password_hash: str,
    password_setup_status: str,
    force_password_change_on_first_login: bool,
) -> None:
    query = text(
        """
        UPDATE dbo.users
        SET
          password_hash = :password_hash,
          password_setup_status = :password_setup_status,
          force_password_change_on_first_login = :force_password_change_on_first_login,
          updated_at = SYSUTCDATETIME()
        WHERE id = :user_id;
        """
    )
    with engine.begin() as connection:
        connection.execute(
            query,
            {
                "user_id": user_id,
                "password_hash": password_hash,
                "password_setup_status": password_setup_status,
                "force_password_change_on_first_login": 1 if force_password_change_on_first_login else 0,
            },
        )


def create_password_reset_token(
    engine: Engine,
    user_id: int,
    token_hash: str,
    purpose: str,
    issued_by_user_id: int | None,
    expires_at: datetime,
) -> None:
    query = text(
        """
        INSERT INTO dbo.password_reset_tokens (
          user_id,
          token_hash,
          purpose,
          issued_by_user_id,
          expires_at
        )
        VALUES (
          :user_id,
          :token_hash,
          :purpose,
          :issued_by_user_id,
          :expires_at
        );
        """
    )
    with engine.begin() as connection:
        connection.execute(
            query,
            {
                "user_id": user_id,
                "token_hash": token_hash,
                "purpose": purpose,
                "issued_by_user_id": issued_by_user_id,
                "expires_at": expires_at,
            },
        )


def find_valid_password_reset_token(
    engine: Engine,
    token_hash: str,
    purpose: str,
) -> dict | None:
    query = text(
        """
        SELECT TOP 1
          prt.id,
          prt.user_id,
          prt.purpose,
          prt.issued_by_user_id,
          prt.expires_at,
          prt.used_at
        FROM dbo.password_reset_tokens AS prt
        WHERE prt.token_hash = :token_hash
        AND prt.purpose = :purpose
        AND prt.used_at IS NULL
        AND prt.expires_at > SYSUTCDATETIME();
        """
    )
    with engine.connect() as connection:
        row = connection.execute(query, {"token_hash": token_hash, "purpose": purpose}).mappings().first()
    return dict(row) if row else None


def find_used_password_reset_token(
    engine: Engine,
    token_hash: str,
    purpose: str,
) -> dict | None:
    query = text(
        """
        SELECT TOP 1
          prt.id,
          prt.user_id,
          prt.purpose,
          prt.issued_by_user_id,
          prt.expires_at,
          prt.used_at
        FROM dbo.password_reset_tokens AS prt
        WHERE prt.token_hash = :token_hash
        AND prt.purpose = :purpose
        AND prt.used_at IS NOT NULL
        ORDER BY prt.used_at DESC;
        """
    )
    with engine.connect() as connection:
        row = connection.execute(query, {"token_hash": token_hash, "purpose": purpose}).mappings().first()
    return dict(row) if row else None


def mark_password_reset_token_used(engine: Engine, token_id: int) -> None:
    query = text(
        """
        UPDATE dbo.password_reset_tokens
        SET used_at = SYSUTCDATETIME()
        WHERE id = :token_id;
        """
    )
    with engine.begin() as connection:
        connection.execute(query, {"token_id": token_id})
