"""Reports API — time-to-fill, source effectiveness, and the dataset catalog
that powers the custom report builder.

All queries aggregate live operational tables. Read endpoints are guarded by
the ``report.read`` permission; Admin bypasses via role_code.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import Engine, text


@dataclass
class TimeToFillSummaryRecord:
    filled_count: int
    avg_days: float | None
    fastest_days: int | None
    fastest_requisition: str | None
    slowest_days: int | None
    slowest_requisition: str | None
    within_sla: int


@dataclass
class TimeToFillBreakdownRecord:
    key: str
    label: str
    avg_days: float | None
    filled_count: int


@dataclass
class SourceEffectivenessRowRecord:
    source: str
    candidates: int
    hired: int


@dataclass
class ReportDatasetRowRecord:
    dataset: str
    rows: list[dict]


def _location_scope_clause(is_admin: bool) -> str:
    """Requisitions are location-bound via branch_id."""
    return "" if is_admin else "AND r.branch_id = :actor_location_id"


def get_time_to_fill_summary(
    engine: Engine,
    actor_location_id: int | None,
    is_admin: bool,
) -> TimeToFillSummaryRecord:
    """Time-to-fill per closed/filled requisition, computed in SQL from
    requisition created_at to the joined application's stage-updated time
    (falling back to the requisition's own updated_at when no candidate
    reached joined)."""
    query = text(
        f"""
        WITH fills AS (
            SELECT
                r.id,
                r.title,
                r.department_name,
                r.sla_days,
                DATEDIFF(
                    DAY,
                    r.created_at,
                    COALESCE(join_hist.changed_at, r.updated_at)
                ) AS days
            FROM dbo.requisitions AS r
            OUTER APPLY (
                SELECT TOP (1) h.changed_at
                FROM dbo.candidate_stage_history AS h
                INNER JOIN dbo.candidate_applications AS ca
                    ON ca.id = h.candidate_application_id
                WHERE ca.requisition_id = r.id
                  AND h.to_stage IN (N'joined', N'hired')
                ORDER BY h.changed_at ASC
            ) AS join_hist
            WHERE r.status IN (N'closed', N'filled')
              {_location_scope_clause(is_admin)}
        )
        SELECT
            COUNT(*) AS filled_count,
            AVG(CAST(days AS FLOAT)) AS avg_days,
            MIN(days) AS fastest_days,
            MAX(days) AS slowest_days,
            SUM(CASE WHEN days <= COALESCE(sla_days, 30) THEN 1 ELSE 0 END) AS within_sla_count
        FROM fills
        WHERE days IS NOT NULL AND days >= 0
        """
    )
    with engine.connect() as connection:
        row = connection.execute(
            query,
            {"actor_location_id": actor_location_id},
        ).mappings().first()

    if row is None or row["filled_count"] == 0:
        return TimeToFillSummaryRecord(0, None, None, None, None, None, 0)

    # Named requisitions for fastest/slowest need a second pass over fills.
    names_query = text(
        f"""
        SELECT TOP (1) r.title
        FROM dbo.requisitions AS r
        OUTER APPLY (
            SELECT TOP (1) h.changed_at
            FROM dbo.candidate_stage_history AS h
            INNER JOIN dbo.candidate_applications AS ca
                ON ca.id = h.candidate_application_id
            WHERE ca.requisition_id = r.id
              AND h.to_stage IN (N'joined', N'hired')
            ORDER BY h.changed_at ASC
        ) AS join_hist
        WHERE r.status IN (N'closed', N'filled')
          {_location_scope_clause(is_admin)}
          AND DATEDIFF(DAY, r.created_at, COALESCE(join_hist.changed_at, r.updated_at)) = :days
        ORDER BY r.created_at ASC
        """
    )
    with engine.connect() as connection:
        fastest_name = connection.execute(
            names_query, {"actor_location_id": actor_location_id, "days": row["fastest_days"]}
        ).scalar_one_or_none()
        slowest_name = connection.execute(
            names_query, {"actor_location_id": actor_location_id, "days": row["slowest_days"]}
        ).scalar_one_or_none()

    return TimeToFillSummaryRecord(
        filled_count=int(row["filled_count"]),
        avg_days=round(float(row["avg_days"]), 1) if row["avg_days"] is not None else None,
        fastest_days=int(row["fastest_days"]) if row["fastest_days"] is not None else None,
        fastest_requisition=fastest_name,
        slowest_days=int(row["slowest_days"]) if row["slowest_days"] is not None else None,
        slowest_requisition=slowest_name,
        within_sla=int(row["within_sla_count"]),
    )


def get_time_to_fill_breakdown(
    engine: Engine,
    group_by: str,
    actor_location_id: int | None,
    is_admin: bool,
) -> list[TimeToFillBreakdownRecord]:
    """Average days-to-fill grouped by department_name (or seniority bucket
    derived from the requisition title)."""
    if group_by == "seniority":
        key_expr = (
            "CASE "
            "WHEN r.title LIKE N'%VP%' OR r.title LIKE N'%President%' THEN N'Executive' "
            "WHEN r.title LIKE N'%Director%' THEN N'Director' "
            "WHEN r.title LIKE N'%Lead%' OR r.title LIKE N'%Principal%' THEN N'Lead' "
            "WHEN r.title LIKE N'%Senior%' OR r.title LIKE N'%Sr%' THEN N'Senior' "
            "WHEN r.title LIKE N'%Junior%' OR r.title LIKE N'%Intern%' OR r.title LIKE N'%Trainee%' THEN N'Junior' "
            "ELSE N'Mid-Level' END"
        )
    else:
        key_expr = "COALESCE(NULLIF(r.department_name, N''), N'Unassigned')"

    query = text(
        f"""
        WITH fills AS (
            SELECT
                {key_expr} AS bucket,
                DATEDIFF(
                    DAY,
                    r.created_at,
                    COALESCE(join_hist.changed_at, r.updated_at)
                ) AS days
            FROM dbo.requisitions AS r
            OUTER APPLY (
                SELECT TOP (1) h.changed_at
                FROM dbo.candidate_stage_history AS h
                INNER JOIN dbo.candidate_applications AS ca
                    ON ca.id = h.candidate_application_id
                WHERE ca.requisition_id = r.id
                  AND h.to_stage IN (N'joined', N'hired')
                ORDER BY h.changed_at ASC
            ) AS join_hist
            WHERE r.status IN (N'closed', N'filled')
              {_location_scope_clause(is_admin)}
        )
        SELECT
            bucket AS [key],
            bucket AS label,
            AVG(CAST(days AS FLOAT)) AS avg_days,
            COUNT(*) AS filled_count
        FROM fills
        WHERE days IS NOT NULL AND days >= 0
        GROUP BY bucket
        ORDER BY avg_days ASC
        """
    )
    with engine.connect() as connection:
        rows = connection.execute(query, {"actor_location_id": actor_location_id}).mappings().all()
    return [
        TimeToFillBreakdownRecord(
            key=str(row["key"]),
            label=str(row["label"]),
            avg_days=round(float(row["avg_days"]), 1) if row["avg_days"] is not None else None,
            filled_count=int(row["filled_count"]),
        )
        for row in rows
    ]


def get_source_effectiveness(
    engine: Engine,
    actor_location_id: int | None,
    is_admin: bool,
) -> list[SourceEffectivenessRowRecord]:
    """Candidates grouped by source; hired = candidates owning an application
    that is joined/hired or carries an accepted/joined offer status."""
    query = text(
        f"""
        SELECT
            c.source AS source,
            COUNT(DISTINCT c.id) AS candidates,
            COUNT(DISTINCT CASE
                WHEN ca.application_status IN (N'joined', N'hired')
                  OR ca.current_stage IN (N'joined', N'hired')
                  OR ca.offer_status IN (N'accepted', N'joined')
                THEN c.id
            END) AS hired
        FROM dbo.candidates AS c
        LEFT JOIN dbo.candidate_applications AS ca
            ON ca.candidate_id = c.id
        WHERE c.status = N'active'
          AND (
            :is_admin = 1
            OR c.created_by_user_id IN (
                SELECT u.id FROM dbo.users AS u WHERE u.location_id = :actor_location_id
            )
            OR ca.requisition_id IN (
                SELECT r.id FROM dbo.requisitions AS r WHERE r.branch_id = :actor_location_id
            )
          )
        GROUP BY c.source
        ORDER BY candidates DESC
        """
    )
    with engine.connect() as connection:
        rows = connection.execute(query, {"actor_location_id": actor_location_id, "is_admin": 1 if is_admin else 0}).mappings().all()
    return [
        SourceEffectivenessRowRecord(
            source=str(row["source"]),
            candidates=int(row["candidates"]),
            hired=int(row["hired"]),
        )
        for row in rows
    ]


def get_report_dataset(
    engine: Engine,
    dataset: str,
    actor_location_id: int | None,
    is_admin: bool,
) -> ReportDatasetRowRecord:
    """Flat rows for the custom report builder's Generate Now action."""
    scope = _location_scope_clause(is_admin)

    if dataset == "time_to_fill":
        query = text(
            f"""
            SELECT
                r.title AS title,
                COALESCE(NULLIF(r.department_name, N''), N'Unassigned') AS department,
                DATEDIFF(DAY, r.created_at, COALESCE(join_hist.changed_at, r.updated_at)) AS days_to_fill,
                COALESCE(r.sla_days, 30) AS sla_days,
                CASE
                    WHEN DATEDIFF(DAY, r.created_at, COALESCE(join_hist.changed_at, r.updated_at))
                         <= COALESCE(r.sla_days, 30) THEN N'within-sla'
                    ELSE N'breached'
                END AS sla_status
            FROM dbo.requisitions AS r
            OUTER APPLY (
                SELECT TOP (1) h.changed_at
                FROM dbo.candidate_stage_history AS h
                INNER JOIN dbo.candidate_applications AS ca
                    ON ca.id = h.candidate_application_id
                WHERE ca.requisition_id = r.id
                  AND h.to_stage IN (N'joined', N'hired')
                ORDER BY h.changed_at ASC
            ) AS join_hist
            WHERE r.status IN (N'closed', N'filled')
              {scope}
        """
        )
    elif dataset == "source_effectiveness":
        query = text(
            f"""
            SELECT
                c.source AS source,
                COUNT(c.id) AS candidates,
                SUM(CASE
                    WHEN ca.application_status IN (N'joined', N'hired')
                      OR ca.current_stage IN (N'joined', N'hired')
                      OR ca.offer_status IN (N'accepted', N'joined')
                    THEN 1 ELSE 0
                END) AS hired
            FROM dbo.candidates AS c
            LEFT JOIN dbo.candidate_applications AS ca ON ca.candidate_id = c.id
            WHERE c.status = N'active'
              AND (
                :is_admin = 1
                OR c.created_by_user_id IN (
                    SELECT u.id FROM dbo.users AS u WHERE u.location_id = :actor_location_id
                )
                OR ca.requisition_id IN (
                    SELECT r.id FROM dbo.requisitions AS r WHERE r.branch_id = :actor_location_id
                )
              )
            GROUP BY c.source
        """
        )
    elif dataset == "pipeline":
        query = text(
            f"""
            SELECT
                r.title AS requisition,
                c.full_name AS candidate,
                ca.current_stage AS stage,
                ca.stage_updated_at AS stage_updated_at
            FROM dbo.candidate_applications AS ca
            INNER JOIN dbo.requisitions AS r ON r.id = ca.requisition_id
            INNER JOIN dbo.candidates AS c ON c.id = ca.candidate_id
            WHERE ca.application_status = N'active'
              {scope}
            ORDER BY ca.stage_updated_at DESC
        """
        )
    elif dataset == "requisitions":
        query = text(
            f"""
            SELECT
                r.title AS title,
                COALESCE(NULLIF(r.department_name, N''), N'Unassigned') AS department,
                r.status AS status,
                r.priority AS priority,
                r.open_positions AS open_positions,
                r.target_close_date AS target_close_date
            FROM dbo.requisitions AS r
            WHERE 1 = 1
              {scope}
            ORDER BY r.created_at DESC
        """
        )
    elif dataset == "sla":
        query = text(
            f"""
            SELECT
                r.title AS mandate,
                c.name AS client,
                COALESCE(r.sla_days, 30) AS sla_target_days,
                CASE
                    WHEN r.status IN (N'closed', N'filled') THEN
                        DATEDIFF(DAY, r.created_at, COALESCE(join_hist.changed_at, r.updated_at))
                    ELSE DATEDIFF(DAY, r.created_at, SYSUTCDATETIME())
                END AS current_days,
                r.status AS status,
                owner_u.full_name AS owner
            FROM dbo.requisitions AS r
            LEFT JOIN dbo.clients AS c ON c.id = r.client_id
            LEFT JOIN dbo.users AS owner_u ON owner_u.id = COALESCE(r.primary_owner_user_id, r.owner_user_id)
            OUTER APPLY (
                SELECT TOP (1) h.changed_at
                FROM dbo.candidate_stage_history AS h
                INNER JOIN dbo.candidate_applications AS ca
                    ON ca.id = h.candidate_application_id
                WHERE ca.requisition_id = r.id
                  AND h.to_stage IN (N'joined', N'hired')
                ORDER BY h.changed_at ASC
            ) AS join_hist
            WHERE 1 = 1
              {scope}
            ORDER BY r.created_at DESC
        """
        )
    elif dataset == "daily_updates":
        query = text(
            """
            SELECT
                du.update_date AS update_date,
                u.full_name AS submitted_by,
                r.title AS requisition,
                du.summary AS summary,
                du.blockers AS blockers
            FROM dbo.daily_updates AS du
            INNER JOIN dbo.users AS u ON u.id = du.submitted_by_user_id
            LEFT JOIN dbo.requisitions AS r ON r.id = du.requisition_id
            ORDER BY du.update_date DESC
        """
        )
    else:
        raise ValueError(f"Unknown dataset: {dataset}")

    with engine.connect() as connection:
        rows = connection.execute(
            query, {"actor_location_id": actor_location_id, "is_admin": 1 if is_admin else 0}
        ).mappings().all()

    # datetime/date objects are not JSON-serializable; stringify them.
    serializable: list[dict] = []
    for row in rows:
        record = {}
        for key, value in dict(row).items():
            if hasattr(value, "isoformat"):
                record[key] = value.isoformat()
            elif value is None:
                record[key] = None
            else:
                record[key] = value
        serializable.append(record)

    return ReportDatasetRowRecord(dataset=dataset, rows=serializable[:500])
