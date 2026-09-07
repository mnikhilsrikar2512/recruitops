from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import Engine, text


@dataclass
class RoleDashboardRecord:
    open_requisitions: int
    active_candidates: int
    active_applications: int
    pending_daily_updates: int


@dataclass
class MyWorkDashboardRecord:
    owned_requisitions: int
    sourced_candidates: int
    active_pipeline_items: int
    submitted_updates: int


@dataclass
class LocationSummaryRecord:
    location_id: int
    location_name: str | None
    open_requisitions: int
    active_candidates: int
    active_applications: int
    submitted_profiles: int
    submitted_updates: int
    joined_applications: int


def get_role_dashboard_counts(
    engine: Engine,
    actor_user_id: int,
    actor_location_id: int | None,
    is_admin: bool,
) -> RoleDashboardRecord:
    query = text(
        """
        SELECT
          (
            SELECT COUNT(*)
            FROM dbo.requisitions AS r
            WHERE r.status IN (N'draft', N'open', N'on-hold')
            AND (:is_admin = 1 OR r.branch_id = :actor_location_id)
          ) AS open_requisitions,
          (
            SELECT COUNT(*)
            FROM dbo.candidates AS c
            WHERE c.profile_status IN (N'draft', N'active')
            AND (
              :is_admin = 1
              OR c.created_by_user_id = :actor_user_id
              OR c.created_by_user_id = :actor_user_id
              OR c.primary_owner_user_id = :actor_user_id
            )
          ) AS active_candidates,
          (
            SELECT COUNT(*)
            FROM dbo.candidate_applications AS ca
            INNER JOIN dbo.requisitions AS r
              ON r.id = ca.requisition_id
            WHERE ca.application_status = N'active'
            AND (
              :is_admin = 1
              OR r.branch_id = :actor_location_id
              OR ca.owner_user_id = :actor_user_id
            )
          ) AS active_applications,
          (
            SELECT COUNT(*)
            FROM dbo.recruiter_daily_updates AS du
            WHERE (
              :is_admin = 1
              OR du.branch_id = :actor_location_id
              OR du.submitted_by_user_id = :actor_user_id
            )
          ) AS pending_daily_updates;
        """
    )
    with engine.connect() as connection:
        row = connection.execute(
            query,
            {
                "actor_user_id": actor_user_id,
                "actor_location_id": actor_location_id,
                "is_admin": 1 if is_admin else 0,
            },
        ).mappings().one()
    return RoleDashboardRecord(**row)


def get_my_work_dashboard_counts(engine: Engine, user_id: int) -> MyWorkDashboardRecord:
    query = text(
        """
        SELECT
          (
            SELECT COUNT(*)
            FROM dbo.requisitions
            WHERE owner_user_id = :user_id
          ) AS owned_requisitions,
          (
            SELECT COUNT(*)
            FROM dbo.candidates
            WHERE created_by_user_id = :user_id
          ) AS sourced_candidates,
          (
            SELECT COUNT(*)
            FROM dbo.candidate_applications
            WHERE owner_user_id = :user_id
            AND application_status = N'active'
          ) AS active_pipeline_items,
          (
            SELECT COUNT(*)
            FROM dbo.recruiter_daily_updates
            WHERE submitted_by_user_id = :user_id
          ) AS submitted_updates;
        """
    )
    with engine.connect() as connection:
        row = connection.execute(query, {"user_id": user_id}).mappings().one()
    return MyWorkDashboardRecord(**row)


def get_location_summary_counts(engine: Engine, location_id: int) -> LocationSummaryRecord:
    query = text(
        """
        SELECT
          l.id AS location_id,
          l.name AS location_name,
          (
            SELECT COUNT(*)
            FROM dbo.requisitions AS r
            WHERE r.branch_id = l.id
            AND r.status IN (N'draft', N'open', N'on-hold')
          ) AS open_requisitions,
          (
            SELECT COUNT(*)
            FROM dbo.candidates AS c
            WHERE c.profile_status IN (N'draft', N'active')
            AND EXISTS (
              SELECT 1
              FROM dbo.candidate_applications AS ca
              INNER JOIN dbo.requisitions AS r
                ON r.id = ca.requisition_id
              WHERE ca.candidate_id = c.id
              AND r.branch_id = l.id
            )
          ) AS active_candidates,
          (
            SELECT COUNT(*)
            FROM dbo.candidate_applications AS ca
            INNER JOIN dbo.requisitions AS r
              ON r.id = ca.requisition_id
            WHERE r.branch_id = l.id
            AND ca.application_status = N'active'
          ) AS active_applications,
          (
            SELECT COUNT(*)
            FROM dbo.candidate_applications AS ca
            INNER JOIN dbo.requisitions AS r
              ON r.id = ca.requisition_id
            WHERE r.branch_id = l.id
            AND ca.current_stage IN (N'submitted', N'submitted_to_client', N'client-review')
          ) AS submitted_profiles,
          (
            SELECT COUNT(*)
            FROM dbo.recruiter_daily_updates AS du
            WHERE du.branch_id = l.id
          ) AS submitted_updates,
          (
            SELECT COUNT(*)
            FROM dbo.candidate_applications AS ca
            INNER JOIN dbo.requisitions AS r
              ON r.id = ca.requisition_id
            WHERE r.branch_id = l.id
            AND ca.application_status = N'joined'
          ) AS joined_applications
        FROM dbo.branches AS l
        WHERE l.id = :location_id;
        """
    )
    with engine.connect() as connection:
        row = connection.execute(query, {"location_id": location_id}).mappings().first()
    if row is None:
        raise RuntimeError("Location summary could not be loaded")
    return LocationSummaryRecord(**row)


def list_company_location_summaries(engine: Engine) -> list[LocationSummaryRecord]:
    query = text(
        """
        SELECT
          l.id AS location_id,
          l.name AS location_name,
          (
            SELECT COUNT(*)
            FROM dbo.requisitions AS r
            WHERE r.branch_id = l.id
            AND r.status IN (N'draft', N'open', N'on-hold')
          ) AS open_requisitions,
          (
            SELECT COUNT(*)
            FROM dbo.candidates AS c
            WHERE c.profile_status IN (N'draft', N'active')
            AND EXISTS (
              SELECT 1
              FROM dbo.candidate_applications AS ca
              INNER JOIN dbo.requisitions AS r
                ON r.id = ca.requisition_id
              WHERE ca.candidate_id = c.id
              AND r.branch_id = l.id
            )
          ) AS active_candidates,
          (
            SELECT COUNT(*)
            FROM dbo.candidate_applications AS ca
            INNER JOIN dbo.requisitions AS r
              ON r.id = ca.requisition_id
            WHERE r.branch_id = l.id
            AND ca.application_status = N'active'
          ) AS active_applications,
          (
            SELECT COUNT(*)
            FROM dbo.candidate_applications AS ca
            INNER JOIN dbo.requisitions AS r
              ON r.id = ca.requisition_id
            WHERE r.branch_id = l.id
            AND ca.current_stage IN (N'submitted', N'submitted_to_client', N'client-review')
          ) AS submitted_profiles,
          (
            SELECT COUNT(*)
            FROM dbo.recruiter_daily_updates AS du
            WHERE du.branch_id = l.id
          ) AS submitted_updates,
          (
            SELECT COUNT(*)
            FROM dbo.candidate_applications AS ca
            INNER JOIN dbo.requisitions AS r
              ON r.id = ca.requisition_id
            WHERE r.branch_id = l.id
            AND ca.application_status = N'joined'
          ) AS joined_applications
        FROM dbo.branches AS l
        ORDER BY l.name ASC, l.id ASC;
        """
    )
    with engine.connect() as connection:
        rows = connection.execute(query).mappings().all()
    return [LocationSummaryRecord(**row) for row in rows]
