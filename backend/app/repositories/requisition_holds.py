"""Requisition holds (Phase 4.12, scripts/024_requisition_holds.sql)."""
from __future__ import annotations

from datetime import date

from sqlalchemy import Connection, Engine, text

from app.repositories.versioning import check_version

_HOLD_COLUMNS = """
    h.id, h.requisition_id, h.reason_code, h.reason_note, h.previous_status, h.expected_resume_date,
    h.held_by_user_id, held_by.full_name AS held_by_name, h.held_at,
    h.resumed_by_user_id, resumed_by.full_name AS resumed_by_name, h.resumed_at, h.resume_note, h.hold_days
"""
_HOLD_FROM = """
    FROM dbo.requisition_holds AS h
    LEFT JOIN dbo.users AS held_by ON held_by.id = h.held_by_user_id
    LEFT JOIN dbo.users AS resumed_by ON resumed_by.id = h.resumed_by_user_id
"""


def find_open_hold(engine: Engine, requisition_id: int) -> dict | None:
    with engine.connect() as connection:
        row = connection.execute(
            text(f"SELECT TOP (1) {_HOLD_COLUMNS} {_HOLD_FROM} WHERE h.requisition_id = :r AND h.resumed_at IS NULL;"),
            {"r": requisition_id},
        ).mappings().first()
    return dict(row) if row else None


def list_holds(engine: Engine, requisition_id: int) -> list[dict]:
    with engine.connect() as connection:
        rows = connection.execute(
            text(f"SELECT {_HOLD_COLUMNS} {_HOLD_FROM} WHERE h.requisition_id = :r ORDER BY h.held_at DESC, h.id DESC;"),
            {"r": requisition_id},
        ).mappings().all()
    return [dict(row) for row in rows]


def put_on_hold(
    engine: Engine,
    requisition_id: int,
    *,
    reason_code: str,
    reason_note: str | None,
    expected_resume_date: date | None,
    user_id: int,
    version: int | None,
) -> None:
    with engine.begin() as connection:
        check_version(connection, "requisitions", requisition_id, version)
        previous = connection.execute(
            text("SELECT status FROM dbo.requisitions WITH (UPDLOCK) WHERE id = :r;"), {"r": requisition_id}
        ).scalar_one()
        connection.execute(
            text(
                """
                INSERT INTO dbo.requisition_holds
                  (requisition_id, reason_code, reason_note, previous_status, expected_resume_date, held_by_user_id)
                VALUES (:r, :code, :note, :previous, :resume_date, :u);
                """
            ),
            {"r": requisition_id, "code": reason_code, "note": reason_note, "previous": previous,
             "resume_date": expected_resume_date, "u": user_id},
        )
        connection.execute(
            text(
                "UPDATE dbo.requisitions SET status = N'on-hold', version = version + 1, "
                "updated_at = SYSUTCDATETIME() WHERE id = :r;"
            ),
            {"r": requisition_id},
        )


def resume_from_hold(
    engine: Engine,
    requisition_id: int,
    *,
    user_id: int,
    note: str | None,
    to_status: str | None,
    version: int | None,
    connection: Connection | None = None,
) -> int:
    """Close the open hold; the hold's days pause the clocks (added to
    hold_days_total, target close date moved out). Returns the hold days."""
    if connection is None:
        with engine.begin() as own:
            return resume_from_hold(engine, requisition_id, user_id=user_id, note=note,
                                    to_status=to_status, version=version, connection=own)
    check_version(connection, "requisitions", requisition_id, version)
    hold = connection.execute(
        text(
            "SELECT id, previous_status, DATEDIFF(DAY, held_at, SYSUTCDATETIME()) AS days "
            "FROM dbo.requisition_holds WITH (UPDLOCK) WHERE requisition_id = :r AND resumed_at IS NULL;"
        ),
        {"r": requisition_id},
    ).mappings().first()
    days = max(int(hold["days"] or 0), 0) if hold else 0
    previous = hold["previous_status"] if hold else "open"
    if previous == "on-hold":
        previous = "open"
    if hold:
        connection.execute(
            text(
                "UPDATE dbo.requisition_holds SET resumed_at = SYSUTCDATETIME(), resumed_by_user_id = :u, "
                "resume_note = :note, hold_days = :days WHERE id = :id;"
            ),
            {"id": hold["id"], "u": user_id, "note": note, "days": days},
        )
    connection.execute(
        text(
            """
            UPDATE dbo.requisitions
            SET status = :status,
                hold_days_total = hold_days_total + :days,
                target_close_date = DATEADD(DAY, :days, target_close_date),
                version = version + 1,
                updated_at = SYSUTCDATETIME()
            WHERE id = :r;
            """
        ),
        {"r": requisition_id, "status": to_status or previous, "days": days},
    )
    return days


def hold_impact(engine: Engine, requisition_id: int) -> dict:
    """What a hold freezes: active candidates (with their owners) and
    interviews still scheduled in the future."""
    with engine.connect() as connection:
        owners = connection.execute(
            text(
                "SELECT ca.owner_user_id, COUNT(*) AS n FROM dbo.candidate_applications AS ca "
                "WHERE ca.requisition_id = :r AND ca.application_status = N'active' GROUP BY ca.owner_user_id;"
            ),
            {"r": requisition_id},
        ).mappings().all()
        interviews = connection.execute(
            text(
                """
                SELECT COUNT(*) FROM dbo.interview_rounds AS i
                INNER JOIN dbo.candidate_applications AS ca ON ca.id = i.candidate_application_id
                WHERE ca.requisition_id = :r AND i.status = N'scheduled'
                  AND (i.scheduled_at IS NULL OR i.scheduled_at >= SYSUTCDATETIME());
                """
            ),
            {"r": requisition_id},
        ).scalar_one()
    return {
        "active_candidates": sum(int(row["n"]) for row in owners),
        "owner_user_ids": [int(row["owner_user_id"]) for row in owners if row["owner_user_id"]],
        "upcoming_interviews": int(interviews or 0),
    }
