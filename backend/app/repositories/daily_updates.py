from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import Engine, text

from app.schemas.daily_update import DailyUpdateCreate, DailyUpdateListFilters


@dataclass
class DailyUpdateRecord:
    id: int
    location_id: int
    submitted_by_user_id: int
    submitted_by_name: str | None
    requisition_id: int | None
    requisition_title: str | None
    update_date: object
    summary: str
    profiles_sourced_count: int | None
    profiles_screened_count: int | None
    profiles_submitted_count: int | None
    interviews_scheduled_count: int | None
    offers_closed_count: int | None
    blockers: str | None
    next_actions: str | None
    submission_status: str
    submitted_at: object
    created_at: object
    updated_at: object


def _daily_update_select_sql() -> str:
    return """
        SELECT
          du.id,
          du.branch_id AS location_id,
          du.submitted_by_user_id,
          u.full_name AS submitted_by_name,
          CAST(NULL AS BIGINT) AS requisition_id,
          CAST(NULL AS NVARCHAR(200)) AS requisition_title,
          du.update_date,
          du.summary,
          CAST(NULL AS INT) AS profiles_sourced_count,
          CAST(NULL AS INT) AS profiles_screened_count,
          du.profiles_escalated_count AS profiles_submitted_count,
          CAST(NULL AS INT) AS interviews_scheduled_count,
          CAST(NULL AS INT) AS offers_closed_count,
          du.blockers,
          du.planned_next_actions AS next_actions,
          N'submitted' AS submission_status,
          du.submitted_at,
          du.created_at,
          du.updated_at
        FROM dbo.recruiter_daily_updates AS du
        LEFT JOIN dbo.users AS u
          ON u.id = du.submitted_by_user_id
    """


def list_daily_updates(engine: Engine, filters: DailyUpdateListFilters) -> tuple[list[DailyUpdateRecord], int]:
    query = text(
        f"""
        WITH filtered_updates AS (
          {_daily_update_select_sql()}
          WHERE (:location_id IS NULL OR du.branch_id = :location_id)
          AND (:tenant_id IS NULL OR du.branch_id IN (SELECT tb.id FROM dbo.branches AS tb WHERE tb.tenant_id = :tenant_id))
          AND (:user_id IS NULL OR du.submitted_by_user_id = :user_id)
          AND (:update_date IS NULL OR du.update_date = :update_date)
        )
        SELECT *, COUNT(*) OVER() AS total_count
        FROM filtered_updates
        ORDER BY update_date DESC, id DESC
        OFFSET :offset ROWS FETCH NEXT :page_size ROWS ONLY;
        """
    )
    with engine.connect() as connection:
        rows = connection.execute(
            query,
            {
                "location_id": filters.location_id,
                "tenant_id": filters.tenant_id,
                "user_id": filters.user_id,
                "requisition_id": filters.requisition_id,
                "update_date": filters.update_date,
                "offset": (filters.page - 1) * filters.page_size,
                "page_size": filters.page_size,
            },
        ).mappings().all()
    total = rows[0]["total_count"] if rows else 0
    return [DailyUpdateRecord(**{key: value for key, value in row.items() if key != "total_count"}) for row in rows], total


def find_daily_update_by_id(engine: Engine, daily_update_id: int) -> DailyUpdateRecord | None:
    query = text(f"{_daily_update_select_sql()} WHERE du.id = :daily_update_id;")
    with engine.connect() as connection:
        row = connection.execute(query, {"daily_update_id": daily_update_id}).mappings().first()
    return DailyUpdateRecord(**row) if row else None


def count_daily_updates_for_user_requisition_date(
    engine: Engine,
    *,
    submitted_by_user_id: int,
    requisition_id: int,
    update_date,
) -> int:
    query = text(
        """
        SELECT COUNT(*) AS total_count
        FROM dbo.recruiter_daily_updates
        WHERE submitted_by_user_id = :submitted_by_user_id
        AND update_date = :update_date;
        """
    )
    with engine.connect() as connection:
        return int(
            connection.execute(
                query,
                {
                    "submitted_by_user_id": submitted_by_user_id,
                    "requisition_id": requisition_id,
                    "update_date": update_date,
                },
            ).scalar_one()
        )


def has_user_requisition_link(engine: Engine, *, user_id: int, requisition_id: int) -> bool:
    query = text(
        """
        SELECT TOP 1 1
        FROM dbo.requisitions AS r
        LEFT JOIN dbo.requisition_assignments AS a
          ON a.requisition_id = r.id
         AND a.assigned_user_id = :user_id
         AND a.status = N'active'
        WHERE r.id = :requisition_id
        AND (r.owner_user_id = :user_id OR a.id IS NOT NULL);
        """
    )
    with engine.connect() as connection:
        row = connection.execute(
            query,
            {"user_id": user_id, "requisition_id": requisition_id},
        ).first()
    return row is not None


def create_daily_update(engine: Engine, location_id: int, payload: DailyUpdateCreate) -> DailyUpdateRecord:
    query = text(
        """
        INSERT INTO dbo.recruiter_daily_updates (
          branch_id,
          submitted_by_user_id,
          update_date,
          summary,
          blockers,
          planned_next_actions,
          submitted_at
        )
        OUTPUT INSERTED.id
        VALUES (
          :location_id,
          :submitted_by_user_id,
          :update_date,
          :summary,
          :blockers,
          :planned_next_actions,
          SYSUTCDATETIME()
        );
        """
    )
    with engine.begin() as connection:
        daily_update_id = connection.execute(
            query,
            {
                "location_id": location_id,
                "submitted_by_user_id": payload.submitted_by_user_id,
                "requisition_id": payload.requisition_id,
                "update_date": payload.update_date,
                "summary": payload.summary,
                "profiles_sourced_count": payload.profiles_sourced_count,
                "profiles_screened_count": payload.profiles_screened_count,
                "profiles_submitted_count": payload.profiles_submitted_count,
                "interviews_scheduled_count": payload.interviews_scheduled_count,
                "offers_closed_count": payload.offers_closed_count,
                "blockers": payload.blockers,
                "planned_next_actions": payload.next_actions,
                "submission_status": payload.submission_status,
            },
        ).scalar_one()
    created = find_daily_update_by_id(engine, int(daily_update_id))
    if created is None:
        raise RuntimeError("Created daily update could not be reloaded")
    return created
