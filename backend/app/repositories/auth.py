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
    # Company (tenant) the user belongs to — scripts/010_tenants.sql.
    tenant_id: int | None = None
    tenant_status: str = "active"
    locked_until: datetime | None = None


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
          b.name AS location_name,
          u.tenant_id,
          t.status AS tenant_status,
          u.locked_until
        FROM dbo.users AS u
        LEFT JOIN dbo.tenants AS t
          ON t.id = u.tenant_id
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
        tenant_id=row.get("tenant_id"),
        tenant_status=row.get("tenant_status") or "active",
        locked_until=row.get("locked_until"),
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
    auth_kind: str = "jwt",
) -> SessionRecord:
    query = text(
        """
        INSERT INTO dbo.user_sessions (
          user_id,
          session_token_hash,
          ip_address,
          user_agent,
          expires_at,
          auth_kind
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
          :expires_at,
          :auth_kind
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
                "auth_kind": auth_kind,
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
        AND ubr.status = N'active'

        UNION

        -- Extra permissions granted directly to the user, on top of their
        -- role(s) -- e.g. the read-only Company Overview bundle granted to
        -- an Admin who also wants full day-to-day visibility, without
        -- needing a second role (the data model only supports one role per
        -- user per branch today; this is the supported way to add reach
        -- beyond that role). Purely additive/union, same as every other
        -- grant here -- see app/api/v1/users.py's extra-permissions routes.
        SELECT DISTINCT p.code AS permission_code
        FROM dbo.user_extra_permissions AS uep
        INNER JOIN dbo.permissions AS p
          ON p.id = uep.permission_id
        WHERE uep.user_id = :user_id
        AND uep.status = N'active';
        """
    )
    with engine.connect() as connection:
        rows = connection.execute(query, {"user_id": user_id}).mappings().all()
    return sorted(row["permission_code"] for row in rows)


# ---- JWT sessions and rotating refresh tokens (Phase 3.1–3.3) ---------------


def find_session_with_user_by_id(engine: Engine, session_id: int) -> SessionWithUserRecord | None:
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
        WHERE s.id = :session_id AND s.auth_kind = N'jwt';
        """
    )
    with engine.connect() as connection:
        row = connection.execute(query, {"session_id": session_id}).mappings().first()
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


def revoke_session(engine: Engine, session_id: int, reason: str) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                UPDATE dbo.user_sessions
                SET revoked_at = SYSUTCDATETIME(), revoked_reason = :reason, updated_at = SYSUTCDATETIME()
                WHERE id = :session_id AND revoked_at IS NULL;
                """
            ),
            {"session_id": session_id, "reason": reason},
        )


def revoke_user_sessions(
    engine: Engine, user_id: int, reason: str, except_session_id: int | None = None
) -> int:
    with engine.begin() as connection:
        result = connection.execute(
            text(
                """
                UPDATE dbo.user_sessions
                SET revoked_at = SYSUTCDATETIME(), revoked_reason = :reason, updated_at = SYSUTCDATETIME()
                WHERE user_id = :user_id AND revoked_at IS NULL
                  AND (:except_id IS NULL OR id <> :except_id);
                """
            ),
            {"user_id": user_id, "reason": reason, "except_id": except_session_id},
        )
    return int(result.rowcount or 0)


def insert_refresh_token(engine: Engine, session_id: int, token_hash: str, expires_at: datetime) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO dbo.user_refresh_tokens (session_id, token_hash, expires_at) "
                "VALUES (:session_id, :token_hash, :expires_at);"
            ),
            {"session_id": session_id, "token_hash": token_hash, "expires_at": expires_at},
        )


@dataclass
class RefreshTokenRecord:
    id: int
    session_id: int
    expires_at: datetime
    used_at: datetime | None


def find_refresh_token(engine: Engine, token_hash: str) -> RefreshTokenRecord | None:
    with engine.connect() as connection:
        row = connection.execute(
            text(
                "SELECT id, session_id, expires_at, used_at FROM dbo.user_refresh_tokens "
                "WHERE token_hash = :token_hash;"
            ),
            {"token_hash": token_hash},
        ).mappings().first()
    return RefreshTokenRecord(**row) if row else None


def mark_refresh_token_used(engine: Engine, token_id: int) -> bool:
    """Atomic: True only for the first caller; a second use is a replay."""
    with engine.begin() as connection:
        result = connection.execute(
            text(
                "UPDATE dbo.user_refresh_tokens SET used_at = SYSUTCDATETIME() "
                "WHERE id = :token_id AND used_at IS NULL;"
            ),
            {"token_id": token_id},
        )
    return (result.rowcount or 0) == 1


def list_active_sessions(engine: Engine, user_id: int) -> list[dict]:
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                """
                SELECT id, ip_address, user_agent, created_at, last_seen_at, expires_at
                FROM dbo.user_sessions
                WHERE user_id = :user_id AND revoked_at IS NULL AND auth_kind = N'jwt'
                  AND expires_at > SYSUTCDATETIME()
                ORDER BY COALESCE(last_seen_at, created_at) DESC;
                """
            ),
            {"user_id": user_id},
        ).mappings().all()
    return [dict(row) for row in rows]


def purge_stale_sessions(engine: Engine, older_than_days: int = 30) -> int:
    """Delete refresh tokens and sessions that ended more than N days ago."""
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                DELETE rt FROM dbo.user_refresh_tokens AS rt
                INNER JOIN dbo.user_sessions AS s ON s.id = rt.session_id
                WHERE COALESCE(s.revoked_at, s.expires_at) < DATEADD(DAY, -:days, SYSUTCDATETIME());
                """
            ),
            {"days": older_than_days},
        )
        result = connection.execute(
            text(
                """
                DELETE FROM dbo.user_sessions
                WHERE COALESCE(revoked_at, expires_at) < DATEADD(DAY, -:days, SYSUTCDATETIME())
                  AND NOT EXISTS (SELECT 1 FROM dbo.user_refresh_tokens AS rt WHERE rt.session_id = dbo.user_sessions.id);
                """
            ),
            {"days": older_than_days},
        )
    return int(result.rowcount or 0)


# ---- failed sign-in lockout (Phase 3.5) ------------------------------------


def record_failed_login(engine: Engine, user_id: int, threshold: int, lock_minutes: int) -> bool:
    """Count a wrong password; at the threshold lock the account for
    ``lock_minutes`` and start counting again. True when this call locked it."""
    with engine.begin() as connection:
        row = connection.execute(
            text(
                """
                UPDATE dbo.users
                SET failed_login_count = CASE WHEN failed_login_count + 1 >= :threshold THEN 0 ELSE failed_login_count + 1 END,
                    locked_until = CASE WHEN failed_login_count + 1 >= :threshold
                                        THEN DATEADD(MINUTE, :minutes, SYSUTCDATETIME()) ELSE locked_until END
                OUTPUT INSERTED.locked_until
                WHERE id = :user_id;
                """
            ),
            {"user_id": user_id, "threshold": threshold, "minutes": lock_minutes},
        ).first()
    return bool(row and row[0])


def reset_failed_logins(engine: Engine, user_id: int) -> None:
    with engine.begin() as connection:
        connection.execute(
            text("UPDATE dbo.users SET failed_login_count = 0, locked_until = NULL "
                 "WHERE id = :user_id AND (failed_login_count <> 0 OR locked_until IS NOT NULL);"),
            {"user_id": user_id},
        )
