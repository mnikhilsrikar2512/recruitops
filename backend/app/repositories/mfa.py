"""TOTP enrolments and recovery codes (Phase 3.6)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import Engine, text


@dataclass
class MfaRecord:
    user_id: int
    totp_secret: str
    enabled_at: datetime | None
    last_used_step: int | None


def find_mfa(engine: Engine, user_id: int) -> MfaRecord | None:
    with engine.connect() as connection:
        row = connection.execute(
            text("SELECT user_id, totp_secret, enabled_at, last_used_step FROM dbo.user_mfa WHERE user_id = :u"),
            {"u": user_id},
        ).mappings().first()
    return MfaRecord(**row) if row else None


def start_enrollment(engine: Engine, user_id: int, secret: str) -> None:
    """New (unconfirmed) secret; replaces any earlier unconfirmed one."""
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                DELETE FROM dbo.user_mfa WHERE user_id = :u AND enabled_at IS NULL;
                INSERT INTO dbo.user_mfa (user_id, totp_secret) VALUES (:u, :s);
                """
            ),
            {"u": user_id, "s": secret},
        )


def confirm_enrollment(engine: Engine, user_id: int, step: int, recovery_hashes: list[str]) -> None:
    with engine.begin() as connection:
        connection.execute(
            text("UPDATE dbo.user_mfa SET enabled_at = SYSUTCDATETIME(), last_used_step = :step WHERE user_id = :u"),
            {"u": user_id, "step": step},
        )
        connection.execute(text("DELETE FROM dbo.user_mfa_recovery_codes WHERE user_id = :u"), {"u": user_id})
        for code_hash in recovery_hashes:
            connection.execute(
                text("INSERT INTO dbo.user_mfa_recovery_codes (user_id, code_hash) VALUES (:u, :h)"),
                {"u": user_id, "h": code_hash},
            )


def claim_step(engine: Engine, user_id: int, step: int) -> bool:
    """A code is usable once: refuse a step at or before the last one used."""
    with engine.begin() as connection:
        result = connection.execute(
            text(
                "UPDATE dbo.user_mfa SET last_used_step = :step "
                "WHERE user_id = :u AND (last_used_step IS NULL OR last_used_step < :step)"
            ),
            {"u": user_id, "step": step},
        )
    return (result.rowcount or 0) == 1


def use_recovery_code(engine: Engine, user_id: int, code_hash: str) -> bool:
    with engine.begin() as connection:
        result = connection.execute(
            text(
                "UPDATE TOP (1) dbo.user_mfa_recovery_codes SET used_at = SYSUTCDATETIME() "
                "WHERE user_id = :u AND code_hash = :h AND used_at IS NULL"
            ),
            {"u": user_id, "h": code_hash},
        )
    return (result.rowcount or 0) == 1


def remaining_recovery_codes(engine: Engine, user_id: int) -> int:
    with engine.connect() as connection:
        return int(connection.execute(
            text("SELECT COUNT(*) FROM dbo.user_mfa_recovery_codes WHERE user_id = :u AND used_at IS NULL"),
            {"u": user_id},
        ).scalar_one())


def remove_mfa(engine: Engine, user_id: int) -> None:
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM dbo.user_mfa_recovery_codes WHERE user_id = :u"), {"u": user_id})
        connection.execute(text("DELETE FROM dbo.user_mfa WHERE user_id = :u"), {"u": user_id})


def admins_without_mfa(engine: Engine, tenant_id: int) -> list[str]:
    """Active users of the company holding the Admin role (default or office
    role) who have no confirmed authenticator."""
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                """
                SELECT DISTINCT u.email
                FROM dbo.users AS u
                LEFT JOIN dbo.user_branch_roles AS ubr ON ubr.user_id = u.id AND ubr.status = N'active'
                INNER JOIN dbo.roles AS r ON r.id IN (u.default_role_id, ubr.role_id)
                LEFT JOIN dbo.user_mfa AS m ON m.user_id = u.id AND m.enabled_at IS NOT NULL
                WHERE u.tenant_id = :t AND u.status = N'active'
                  AND r.code = N'admin' AND r.tenant_id IS NULL
                  AND m.user_id IS NULL
                ORDER BY u.email;
                """
            ),
            {"t": tenant_id},
        ).all()
    return [row[0] for row in rows]
