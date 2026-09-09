from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time

from sqlalchemy import Engine, text
from sqlalchemy.engine import RowMapping

from app.schemas.pagination import PaginationMeta
from app.schemas.portal import (
    PortalAccountCreate,
    PortalAccountListFilters,
    PortalAccountUpdate,
    PortalAvailabilityFilters,
    PortalSlotCreate,
    PortalSlotListFilters,
    PortalSlotUpdate,
)


@dataclass
class PortalAccountRecord:
    id: int
    branch_id: int
    platform_name: str
    account_name: str
    login_identifier: str | None
    status: str
    ownership_type: str
    owned_by_user_id: int | None
    owned_by_user_name: str | None
    branch_name: str | None
    is_shared: bool
    has_full_access: bool
    daily_usage_limit_hours: float | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


@dataclass
class PortalSlotRecord:
    id: int
    portal_account_id: int
    assigned_user_id: int
    assigned_user_name: str | None
    usage_date: date
    start_time: time
    end_time: time
    status: str
    approved_by_user_id: int | None
    approved_by_user_name: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


_ACCOUNT_SELECT = """
    SELECT
      pa.id,
      pa.branch_id,
      pa.platform_name,
      pa.account_name,
      pa.login_identifier,
      pa.status,
      pa.ownership_type,
      pa.owned_by_user_id,
      u.full_name AS owned_by_user_name,
      b.name AS branch_name,
      pa.is_shared,
      pa.has_full_access,
      pa.daily_usage_limit_hours,
      pa.notes,
      pa.created_at,
      pa.updated_at
    FROM dbo.portal_accounts AS pa
    LEFT JOIN dbo.users AS u ON u.id = pa.owned_by_user_id
    LEFT JOIN dbo.branches AS b ON b.id = pa.branch_id
"""

_SLOT_SELECT = """
    SELECT
      s.id,
      s.portal_account_id,
      s.assigned_user_id,
      u.full_name AS assigned_user_name,
      s.usage_date,
      s.start_time,
      s.end_time,
      s.status,
      s.approved_by_user_id,
      au.full_name AS approved_by_user_name,
      s.notes,
      s.created_at,
      s.updated_at
    FROM dbo.portal_account_slots AS s
    LEFT JOIN dbo.users AS u ON u.id = s.assigned_user_id
    LEFT JOIN dbo.users AS au ON au.id = s.approved_by_user_id
"""


def _map_account(row: RowMapping) -> PortalAccountRecord:
    return PortalAccountRecord(
        id=row["id"],
        branch_id=row["branch_id"],
        platform_name=row["platform_name"],
        account_name=row["account_name"],
        login_identifier=row["login_identifier"],
        status=row["status"],
        ownership_type=row["ownership_type"],
        owned_by_user_id=row["owned_by_user_id"],
        owned_by_user_name=row["owned_by_user_name"],
        branch_name=row["branch_name"],
        is_shared=bool(row["is_shared"]),
        has_full_access=bool(row["has_full_access"]),
        daily_usage_limit_hours=row["daily_usage_limit_hours"],
        notes=row["notes"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _map_slot(row: RowMapping) -> PortalSlotRecord:
    return PortalSlotRecord(
        id=row["id"],
        portal_account_id=row["portal_account_id"],
        assigned_user_id=row["assigned_user_id"],
        assigned_user_name=row["assigned_user_name"],
        usage_date=row["usage_date"],
        start_time=row["start_time"],
        end_time=row["end_time"],
        status=row["status"],
        approved_by_user_id=row["approved_by_user_id"],
        approved_by_user_name=row["approved_by_user_name"],
        notes=row["notes"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def list_portal_accounts(
    engine: Engine, filters: PortalAccountListFilters
) -> tuple[list[PortalAccountRecord], int]:
    base_where = """
        WHERE (:status IS NULL OR pa.status = :status)
        AND (:platform IS NULL OR pa.platform_name LIKE '%' + :platform + '%')
        AND (:ownership_type IS NULL OR pa.ownership_type = :ownership_type)
        AND (
          :search IS NULL
          OR pa.platform_name LIKE '%' + :search + '%'
          OR pa.account_name LIKE '%' + :search + '%'
          OR pa.login_identifier LIKE '%' + :search + '%'
        )
    """
    page_query = text(
        _ACCOUNT_SELECT
        + base_where
        + """
        ORDER BY pa.updated_at DESC, pa.id DESC
        OFFSET :offset ROWS FETCH NEXT :page_size ROWS ONLY;
        """
    )
    count_query = text(
        "SELECT COUNT(*) AS total_count FROM dbo.portal_accounts AS pa" + base_where + ";"
    )
    params = {
        "status": filters.status,
        "platform": filters.platform,
        "ownership_type": filters.ownership_type,
        "search": filters.search,
        "offset": (filters.page - 1) * filters.page_size,
        "page_size": filters.page_size,
    }

    with engine.connect() as connection:
        rows = connection.execute(page_query, params).mappings().all()
        total = connection.execute(count_query, params).scalar_one()

    return [_map_account(row) for row in rows], int(total or 0)


def find_portal_account_by_id(engine: Engine, portal_account_id: int) -> PortalAccountRecord | None:
    query = text(_ACCOUNT_SELECT + " WHERE pa.id = :portal_account_id;")
    with engine.connect() as connection:
        row = connection.execute(query, {"portal_account_id": portal_account_id}).mappings().first()
    return _map_account(row) if row else None


def user_exists(engine: Engine, user_id: int) -> bool:
    with engine.connect() as connection:
        row = connection.execute(
            text("SELECT 1 FROM dbo.users WHERE id = :user_id;"), {"user_id": user_id}
        ).first()
    return row is not None


def branch_exists(engine: Engine, branch_id: int) -> bool:
    with engine.connect() as connection:
        row = connection.execute(
            text("SELECT 1 FROM dbo.branches WHERE id = :branch_id;"), {"branch_id": branch_id}
        ).first()
    return row is not None


def create_portal_account(
    engine: Engine, payload: PortalAccountCreate, actor_user_id: int | None
) -> PortalAccountRecord:
    owned_by_user_id = payload.owned_by_user_id
    if owned_by_user_id is None and payload.ownership_type == "personal":
        owned_by_user_id = actor_user_id

    query = text(
        """
        INSERT INTO dbo.portal_accounts
          (branch_id, platform_name, account_name, login_identifier, status,
           ownership_type, owned_by_user_id, is_shared, has_full_access,
           daily_usage_limit_hours, notes)
        OUTPUT INSERTED.id
        VALUES
          (:branch_id, :platform_name, :account_name, :login_identifier, :status,
           :ownership_type, :owned_by_user_id, :is_shared, :has_full_access,
           :daily_usage_limit_hours, :notes);
        """
    )
    with engine.begin() as connection:
        new_id = connection.execute(
            query,
            {
                "branch_id": payload.branch_id,
                "platform_name": payload.platform_name,
                "account_name": payload.account_name,
                "login_identifier": payload.login_identifier,
                "status": payload.status,
                "ownership_type": payload.ownership_type,
                "owned_by_user_id": owned_by_user_id,
                "is_shared": payload.is_shared,
                "has_full_access": payload.has_full_access,
                "daily_usage_limit_hours": payload.daily_usage_limit_hours,
                "notes": payload.notes,
            },
        ).scalar_one()

    return find_portal_account_by_id(engine, new_id)  # type: ignore[return-value]


def update_portal_account(
    engine: Engine, portal_account_id: int, payload: PortalAccountUpdate
) -> PortalAccountRecord:
    query = text(
        """
        UPDATE dbo.portal_accounts
        SET
          platform_name = COALESCE(:platform_name, platform_name),
          account_name = COALESCE(:account_name, account_name),
          login_identifier = COALESCE(:login_identifier, login_identifier),
          status = COALESCE(:status, status),
          ownership_type = COALESCE(:ownership_type, ownership_type),
          owned_by_user_id = COALESCE(:owned_by_user_id, owned_by_user_id),
          is_shared = COALESCE(:is_shared, is_shared),
          has_full_access = COALESCE(:has_full_access, has_full_access),
          daily_usage_limit_hours = COALESCE(:daily_usage_limit_hours, daily_usage_limit_hours),
          notes = COALESCE(:notes, notes),
          updated_at = SYSDATETIME()
        WHERE id = :portal_account_id;
        """
    )
    with engine.begin() as connection:
        connection.execute(
            query,
            {
                "portal_account_id": portal_account_id,
                "platform_name": payload.platform_name,
                "account_name": payload.account_name,
                "login_identifier": payload.login_identifier,
                "status": payload.status,
                "ownership_type": payload.ownership_type,
                "owned_by_user_id": payload.owned_by_user_id,
                "is_shared": payload.is_shared,
                "has_full_access": payload.has_full_access,
                "daily_usage_limit_hours": payload.daily_usage_limit_hours,
                "notes": payload.notes,
            },
        )
    return find_portal_account_by_id(engine, portal_account_id)  # type: ignore[return-value]


def list_portal_slots(
    engine: Engine, portal_account_id: int, filters: PortalSlotListFilters
) -> tuple[list[PortalSlotRecord], int]:
    base_where = """
        WHERE s.portal_account_id = :portal_account_id
        AND (:status IS NULL OR s.status = :status)
        AND (:usage_date IS NULL OR s.usage_date = :usage_date)
    """
    page_query = text(
        _SLOT_SELECT
        + base_where
        + """
        ORDER BY s.usage_date DESC, s.start_time DESC, s.id DESC
        OFFSET :offset ROWS FETCH NEXT :page_size ROWS ONLY;
        """
    )
    count_query = text(
        "SELECT COUNT(*) AS total_count FROM dbo.portal_account_slots AS s" + base_where + ";"
    )
    params = {
        "portal_account_id": portal_account_id,
        "status": filters.status,
        "usage_date": filters.usage_date,
        "offset": (filters.page - 1) * filters.page_size,
        "page_size": filters.page_size,
    }

    with engine.connect() as connection:
        rows = connection.execute(page_query, params).mappings().all()
        total = connection.execute(count_query, params).scalar_one()

    return [_map_slot(row) for row in rows], int(total)


def find_portal_slot_by_id(
    engine: Engine, portal_account_id: int, slot_id: int
) -> PortalSlotRecord | None:
    query = text(
        _SLOT_SELECT + " WHERE s.id = :slot_id AND s.portal_account_id = :portal_account_id;"
    )
    with engine.connect() as connection:
        row = connection.execute(
            query, {"slot_id": slot_id, "portal_account_id": portal_account_id}
        ).mappings().first()
    return _map_slot(row) if row else None


def create_portal_slot(
    engine: Engine, portal_account_id: int, payload: PortalSlotCreate
) -> PortalSlotRecord:
    query = text(
        """
        INSERT INTO dbo.portal_account_slots
          (portal_account_id, assigned_user_id, usage_date, start_time, end_time, status, notes)
        OUTPUT INSERTED.id
        VALUES
          (:portal_account_id, :assigned_user_id, :usage_date, :start_time, :end_time, :status, :notes);
        """
    )
    with engine.begin() as connection:
        new_id = connection.execute(
            query,
            {
                "portal_account_id": portal_account_id,
                "assigned_user_id": payload.assigned_user_id,
                "usage_date": payload.usage_date,
                "start_time": payload.start_time,
                "end_time": payload.end_time,
                "status": payload.status,
                "notes": payload.notes,
            },
        ).scalar_one()
    return find_portal_slot_by_id(engine, portal_account_id, new_id)  # type: ignore[return-value]


def update_portal_slot(
    engine: Engine, portal_account_id: int, slot_id: int, payload: PortalSlotUpdate
) -> PortalSlotRecord:
    query = text(
        """
        UPDATE dbo.portal_account_slots
        SET
          assigned_user_id = COALESCE(:assigned_user_id, assigned_user_id),
          usage_date = COALESCE(:usage_date, usage_date),
          start_time = COALESCE(:start_time, start_time),
          end_time = COALESCE(:end_time, end_time),
          status = COALESCE(:status, status),
          notes = COALESCE(:notes, notes),
          updated_at = SYSDATETIME()
        WHERE id = :slot_id AND portal_account_id = :portal_account_id;
        """
    )
    with engine.begin() as connection:
        connection.execute(
            query,
            {
                "portal_account_id": portal_account_id,
                "slot_id": slot_id,
                "assigned_user_id": payload.assigned_user_id,
                "usage_date": payload.usage_date,
                "start_time": payload.start_time,
                "end_time": payload.end_time,
                "status": payload.status,
                "notes": payload.notes,
            },
        )
    return find_portal_slot_by_id(engine, portal_account_id, slot_id)  # type: ignore[return-value]


def delete_portal_slot(engine: Engine, portal_account_id: int, slot_id: int) -> bool:
    with engine.begin() as connection:
        result = connection.execute(
            text(
                "DELETE FROM dbo.portal_account_slots "
                "WHERE id = :slot_id AND portal_account_id = :portal_account_id;"
            ),
            {"slot_id": slot_id, "portal_account_id": portal_account_id},
        )
    return result.rowcount > 0


def summarize_portal_usage_by_week(
    engine: Engine, weeks_back: int = 6
) -> list[dict[str, object]]:
    """Booked minutes per platform per ISO week (Monday-start), recent weeks.

    Counts every non-cancelled slot (planned, approved, completed) so the report
    reflects committed portal time, not just drafts.
    """
    query = text(
        """
        SELECT
          pa.platform_name,
          DATEADD(
            DAY,
            -((DATEPART(WEEKDAY, s.usage_date) + @@DATEFIRST - 2) % 7),
            CAST(s.usage_date AS date)
          ) AS week_start,
          SUM(DATEDIFF(MINUTE, s.start_time, s.end_time)) AS booked_minutes
        FROM dbo.portal_account_slots AS s
        JOIN dbo.portal_accounts AS pa ON pa.id = s.portal_account_id
        WHERE s.status <> 'cancelled'
        AND s.usage_date >= DATEADD(WEEK, -:weeks_back, CAST(GETDATE() AS date))
        GROUP BY pa.platform_name,
                 DATEADD(
                   DAY,
                   -((DATEPART(WEEKDAY, s.usage_date) + @@DATEFIRST - 2) % 7),
                   CAST(s.usage_date AS date)
                 )
        ORDER BY pa.platform_name, week_start;
        """
    )
    with engine.connect() as connection:
        rows = connection.execute(query, {"weeks_back": weeks_back}).mappings().all()

    return [
        {
            "platform_name": row["platform_name"],
            "week_start": row["week_start"],
            "booked_minutes": int(row["booked_minutes"] or 0),
        }
        for row in rows
    ]


def list_portal_availability(
    engine: Engine, filters: PortalAvailabilityFilters | None = None
) -> list[dict[str, object]]:
    filters = filters or PortalAvailabilityFilters()
    query = text(
        """
        SELECT
          pa.id AS portal_account_id,
          pa.platform_name,
          pa.account_name,
          b.name AS branch_name,
          pa.is_shared,
          pa.has_full_access,
          pa.daily_usage_limit_hours,
          COALESCE(SUM(
            CASE
              WHEN s.status = 'planned'
                   AND (:usage_date IS NULL OR s.usage_date = :usage_date)
              THEN DATEDIFF(MINUTE, s.start_time, s.end_time)
              ELSE 0
            END
          ), 0) AS booked_minutes
        FROM dbo.portal_accounts AS pa
        LEFT JOIN dbo.branches AS b ON b.id = pa.branch_id
        LEFT JOIN dbo.portal_account_slots AS s ON s.portal_account_id = pa.id
        WHERE pa.status = 'active'
        AND (:platform IS NULL OR pa.platform_name LIKE '%' + :platform + '%')
        AND (:branch_id IS NULL OR pa.branch_id = :branch_id)
        GROUP BY pa.id, pa.platform_name, pa.account_name, b.name,
                 pa.is_shared, pa.has_full_access, pa.daily_usage_limit_hours
        ORDER BY pa.platform_name, pa.account_name;
        """
    )
    with engine.connect() as connection:
        rows = connection.execute(
            query,
            {
                "platform": filters.platform,
                "branch_id": filters.branch_id,
                "usage_date": filters.usage_date,
            },
        ).mappings().all()

    return [
        {
            "portal_account_id": row["portal_account_id"],
            "platform_name": row["platform_name"],
            "account_name": row["account_name"],
            "branch_name": row["branch_name"],
            "is_shared": bool(row["is_shared"]),
            "has_full_access": bool(row["has_full_access"]),
            "daily_usage_limit_hours": row["daily_usage_limit_hours"],
            "booked_minutes": int(row["booked_minutes"] or 0),
        }
        for row in rows
    ]
