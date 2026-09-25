from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import Engine, text


@dataclass
class LoginUserRecord:
    id: int
    employee_code: str | None
    full_name: str
    email: str
    phone: str | None
    password_hash: str
    status: str
    business_title: str | None
    force_password_change_on_first_login: bool
    location_id: int | None
    role_id: int
    role_code: str
    role_name: str
    location_code: str | None
    location_name: str | None


@dataclass
class SessionRecord:
    id: int
    user_id: int
    session_token_hash: str
    expires_at: datetime
    revoked_at: datetime | None
    last_seen_at: datetime | None


@dataclass
class SessionWithUserRecord:
    session: SessionRecord
    user: LoginUserRecord


def _user_auth_select_sql() -> str:
    return """
        SELECT
          u.id AS user_id,
          u.employee_code,
          u.full_name,
          u.email,
          u.phone,
          u.password_hash,
          u.status,
          u.business_title,
          u.force_password_change_on_first_login,
          ubr.branch_id AS location_id,
          r.id AS role_id,
          r.code AS role_code,
          r.name AS role_name,
          b.code AS location_code,
          b.name AS location_name
        FROM dbo.users AS u
        INNER JOIN dbo.roles AS r
          ON r.id = u.default_role_id
        LEFT JOIN dbo.user_branch_roles AS ubr
          ON ubr.user_id = u.id
         AND ubr.is_primary = 1
         AND ubr.status = N'active'
        LEFT JOIN dbo.branches AS b
          ON b.id = ubr.branch_id
    """


def _map_user(row) -> LoginUserRecord:
    return LoginUserRecord(
        id=row["user_id"],
        employee_code=row["employee_code"],
        full_name=row["full_name"],
        email=row["email"],
        phone=row["phone"],
        password_hash=row["password_hash"],
        status=row["status"],
        business_title=row["business_title"],
        force_password_change_on_first_login=row["force_password_change_on_first_login"],
        location_id=row["location_id"],
        role_id=row["role_id"],
        role_code=row["role_code"],
        role_name=row["role_name"],
        location_code=row["location_code"],
        location_name=row["location_name"],
    )


def find_user_for_login(engine: Engine, email: str) -> LoginUserRecord | None:
    query = text(
        f"""
        SELECT TOP 1 *
        FROM (
          {_user_auth_select_sql()}
        ) AS auth_users
        WHERE LOWER(email) = LOWER(:email);
        """
    )
    with engine.connect() as connection:
        row = connection.execute(query, {"email": email}).mappings().first()
    return _map_user(row) if row else None


def insert_user_session(
    engine: Engine,
    user_id: int,
    session_token_hash: str,
    ip_address: str | None,
    user_agent: str | None,
    expires_at: datetime,
) -> SessionRecord:
    query = text(
        """
        INSERT INTO dbo.user_sessions (
          user_id,
          session_token_hash,
          ip_address,
          user_agent,
          expires_at
        )
        OUTPUT
          INSERTED.id,
          INSERTED.user_id,
          INSERTED.session_token_hash,
          INSERTED.expires_at,
          INSERTED.revoked_at,
          INSERTED.last_seen_at
        VALUES (
          :user_id,
          :session_token_hash,
          :ip_address,
          :user_agent,
          :expires_at
        );
        """
    )
    with engine.begin() as connection:
        row = connection.execute(
            query,
            {
                "user_id": user_id,
                "session_token_hash": session_token_hash,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "expires_at": expires_at,
            },
        ).mappings().one()
    return SessionRecord(**row)


def find_session_with_user_by_hash(engine: Engine, session_token_hash: str) -> SessionWithUserRecord | None:
    query = text(
        f"""
        SELECT TOP 1
          s.id AS session_id,
          s.user_id AS session_user_id,
          s.session_token_hash,
          s.expires_at,
          s.revoked_at,
          s.last_seen_at,
          auth_users.*
        FROM dbo.user_sessions AS s
        INNER JOIN (
          {_user_auth_select_sql()}
        ) AS auth_users
          ON auth_users.user_id = s.user_id
        WHERE s.session_token_hash = :session_token_hash;
        """
    )
    with engine.connect() as connection:
        row = connection.execute(query, {"session_token_hash": session_token_hash}).mappings().first()
    if not row:
        return None
    session = SessionRecord(
        id=row["session_id"],
        user_id=row["session_user_id"],
        session_token_hash=row["session_token_hash"],
        expires_at=row["expires_at"],
        revoked_at=row["revoked_at"],
        last_seen_at=row["last_seen_at"],
    )
    return SessionWithUserRecord(session=session, user=_map_user(row))


def touch_session(engine: Engine, session_id: int) -> None:
    query = text(
        """
        UPDATE dbo.user_sessions
        SET
          last_seen_at = SYSUTCDATETIME(),
          updated_at = SYSUTCDATETIME()
        WHERE id = :session_id;
        """
    )
    with engine.begin() as connection:
        connection.execute(query, {"session_id": session_id})


def revoke_session_by_hash(engine: Engine, session_token_hash: str) -> None:
    query = text(
        """
        UPDATE dbo.user_sessions
        SET
          revoked_at = SYSUTCDATETIME(),
          updated_at = SYSUTCDATETIME()
        WHERE session_token_hash = :session_token_hash
        AND revoked_at IS NULL;
        """
    )
    with engine.begin() as connection:
        connection.execute(query, {"session_token_hash": session_token_hash})


def update_last_login(engine: Engine, user_id: int) -> None:
    query = text(
        """
        UPDATE dbo.users
        SET
          last_login_at = SYSUTCDATETIME(),
          updated_at = SYSUTCDATETIME()
        WHERE id = :user_id;
        """
    )
    with engine.begin() as connection:
        connection.execute(query, {"user_id": user_id})


def list_resolved_permissions(engine: Engine, user_id: int) -> list[str]:
    query = text(
        """
        SELECT DISTINCT p.code AS permission_code
        FROM dbo.users AS u
        INNER JOIN dbo.role_permissions AS rp
          ON rp.role_id = u.default_role_id
        INNER JOIN dbo.permissions AS p
          ON p.id = rp.permission_id
        WHERE u.id = :user_id

        UNION

        SELECT DISTINCT p.code AS permission_code
        FROM dbo.user_branch_roles AS ubr
        INNER JOIN dbo.role_permissions AS rp
          ON rp.role_id = ubr.role_id
        INNER JOIN dbo.permissions AS p
          ON p.id = rp.permission_id
        WHERE ubr.user_id = :user_id
        AND ubr.status = N'active';
        """
    )
    with engine.connect() as connection:
        rows = connection.execute(query, {"user_id": user_id}).mappings().all()
    return sorted(row["permission_code"] for row in rows)
