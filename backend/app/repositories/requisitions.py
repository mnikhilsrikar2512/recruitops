from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import Engine, text
from sqlalchemy.engine import RowMapping

from app.schemas.requisition import (
    RequisitionAssignmentCreate,
    RequisitionCreate,
    RequisitionListFilters,
    RequisitionStatusUpdate,
    RequisitionUpdate,
)


@dataclass
class RequisitionRecord:
    id: int
    location_id: int
    requisition_code: str | None
    client_id: int | None
    client_name: str | None
    primary_contact_id: int | None
    primary_contact_name: str | None
    secondary_contact_id: int | None
    secondary_contact_name: str | None
    title: str
    primary_owner_user_id: int
    primary_owner_name: str | None
    delivery_owner_user_id: int | None
    delivery_owner_name: str | None
    priority: str
    status: str
    openings_count: int
    target_closure_date: object
    client_round_required: bool
    job_description: str
    acceptable_career_gap_months: int | None
    profile_update_window_text: str | None
    employment_type: str | None
    work_mode: str | None
    stage_template_id: int | None
    created_at: object
    updated_at: object
    must_have_skills: list[str]
    good_to_have_skills: list[str]


@dataclass
class RequisitionAssignmentRecord:
    id: int
    location_id: int
    requisition_id: int
    assigned_user_id: int
    assigned_user_name: str | None
    assignment_type: str
    assigned_by_user_id: int
    assigned_by_user_name: str | None
    assigned_at: object
    status: str
    created_at: object
    updated_at: object


def _requisition_select_sql() -> str:
    return """
        SELECT
          r.id,
          r.branch_id AS location_id,
          CAST(NULL AS NVARCHAR(50)) AS requisition_code,
          r.client_company_id AS client_id,
          c.name AS client_name,
          CAST(NULL AS BIGINT) AS primary_contact_id,
          CAST(NULL AS NVARCHAR(200)) AS primary_contact_name,
          CAST(NULL AS BIGINT) AS secondary_contact_id,
          CAST(NULL AS NVARCHAR(200)) AS secondary_contact_name,
          r.title,
          r.owner_user_id AS primary_owner_user_id,
          primary_owner.full_name AS primary_owner_name,
          CAST(NULL AS BIGINT) AS delivery_owner_user_id,
          CAST(NULL AS NVARCHAR(200)) AS delivery_owner_name,
          r.priority,
          r.status,
          r.open_positions,
          r.target_close_date,
          r.client_round_required,
          r.job_description,
          CAST(NULL AS INT) AS acceptable_career_gap_months,
          r.important_notes AS preferred_update_time_text,
          CAST(NULL AS NVARCHAR(50)) AS employment_type,
          CAST(NULL AS NVARCHAR(50)) AS work_mode,
          CAST(NULL AS BIGINT) AS pipeline_template_id,
          r.created_at,
          r.updated_at
        FROM dbo.requisitions AS r
        LEFT JOIN dbo.client_companies AS c
          ON c.id = r.client_company_id
        LEFT JOIN dbo.users AS primary_owner
          ON primary_owner.id = r.owner_user_id
    """


def _map_requisition(row: RowMapping, must_have_skills: list[str], good_to_have_skills: list[str]) -> RequisitionRecord:
    return RequisitionRecord(
        id=row["id"],
        location_id=row["location_id"],
        requisition_code=row["requisition_code"],
        client_id=row["client_id"],
        client_name=row["client_name"],
        primary_contact_id=row["primary_contact_id"],
        primary_contact_name=row["primary_contact_name"],
        secondary_contact_id=row["secondary_contact_id"],
        secondary_contact_name=row["secondary_contact_name"],
        title=row["title"],
        primary_owner_user_id=row["primary_owner_user_id"],
        primary_owner_name=row["primary_owner_name"],
        delivery_owner_user_id=row["delivery_owner_user_id"],
        delivery_owner_name=row["delivery_owner_name"],
        priority=row["priority"],
        status=row["status"],
        openings_count=row["open_positions"],
        target_closure_date=row["target_close_date"],
        client_round_required=row["client_round_required"],
        job_description=row["job_description"],
        acceptable_career_gap_months=row["acceptable_career_gap_months"],
        profile_update_window_text=row["preferred_update_time_text"],
        employment_type=row["employment_type"],
        work_mode=row["work_mode"],
        stage_template_id=row["pipeline_template_id"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        must_have_skills=must_have_skills,
        good_to_have_skills=good_to_have_skills,
    )


def _map_assignment(row: RowMapping) -> RequisitionAssignmentRecord:
    return RequisitionAssignmentRecord(
        id=row["id"],
        location_id=row["location_id"],
        requisition_id=row["requisition_id"],
        assigned_user_id=row["assigned_user_id"],
        assigned_user_name=row["assigned_user_name"],
        assignment_type=row["assignment_type"],
        assigned_by_user_id=row["assigned_by_user_id"],
        assigned_by_user_name=row["assigned_by_user_name"],
        assigned_at=row["assigned_at"],
        status=row["status"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def list_requisition_skills(engine: Engine, requisition_id: int) -> tuple[list[str], list[str]]:
    query = text(
        """
        SELECT skill_name, skill_type, priority_order
        FROM dbo.requisition_skill_requirements
        WHERE requisition_id = :requisition_id
        ORDER BY skill_type, priority_order, id;
        """
    )
    with engine.connect() as connection:
        rows = connection.execute(query, {"requisition_id": requisition_id}).mappings().all()
    must_have = [row["skill_name"] for row in rows if row["skill_type"] == "must-have"]
    good_to_have = [row["skill_name"] for row in rows if row["skill_type"] == "good-to-have"]
    return must_have, good_to_have


def list_requisitions(engine: Engine, filters: RequisitionListFilters) -> tuple[list[RequisitionRecord], int]:
    query = text(
        f"""
        WITH filtered_requisitions AS (
          {_requisition_select_sql()}
          WHERE (:location_id IS NULL OR r.branch_id = :location_id)
          AND (:client_id IS NULL OR r.client_company_id = :client_id)
          AND (:primary_owner_user_id IS NULL OR r.owner_user_id = :primary_owner_user_id)
          AND (:delivery_owner_user_id IS NULL OR :delivery_owner_user_id IS NOT NULL AND 1 = 0)
          AND (:status IS NULL OR r.status = :status)
          AND (:priority IS NULL OR r.priority = :priority)
          AND (:due_date_from IS NULL OR r.target_close_date >= :due_date_from)
          AND (:due_date_to IS NULL OR r.target_close_date <= :due_date_to)
          AND (
            :search IS NULL
            OR r.title LIKE '%' + :search + '%'
            OR c.name LIKE '%' + :search + '%'
          )
        )
        SELECT *, COUNT(*) OVER() AS total_count
        FROM filtered_requisitions
        ORDER BY updated_at DESC, id DESC
        OFFSET :offset ROWS FETCH NEXT :page_size ROWS ONLY;
        """
    )
    with engine.connect() as connection:
        rows = connection.execute(
            query,
            {
                "location_id": filters.location_id,
                "client_id": filters.client_id,
                "primary_owner_user_id": filters.primary_owner_user_id,
                "delivery_owner_user_id": filters.delivery_owner_user_id,
                "status": filters.status,
                "priority": filters.priority,
                "due_date_from": filters.due_date_from,
                "due_date_to": filters.due_date_to,
                "search": filters.search,
                "offset": (filters.page - 1) * filters.page_size,
                "page_size": filters.page_size,
            },
        ).mappings().all()
    total = rows[0]["total_count"] if rows else 0
    items: list[RequisitionRecord] = []
    for row in rows:
        must_have, good_to_have = list_requisition_skills(engine, row["id"])
        items.append(_map_requisition(row, must_have, good_to_have))
    return items, total


def find_requisition_by_id(engine: Engine, requisition_id: int) -> RequisitionRecord | None:
    query = text(f"{_requisition_select_sql()} WHERE r.id = :requisition_id;")
    with engine.connect() as connection:
        row = connection.execute(query, {"requisition_id": requisition_id}).mappings().first()
    if not row:
        return None
    must_have, good_to_have = list_requisition_skills(engine, requisition_id)
    return _map_requisition(row, must_have, good_to_have)


def count_active_requisition_assignments(engine: Engine, requisition_id: int) -> int:
    query = text(
        """
        SELECT COUNT(*) AS total_count
        FROM dbo.requisition_assignments
        WHERE requisition_id = :requisition_id
        AND status = N'active';
        """
    )
    with engine.connect() as connection:
        return int(connection.execute(query, {"requisition_id": requisition_id}).scalar_one())


def count_active_requisition_applications(engine: Engine, requisition_id: int) -> int:
    query = text(
        """
        SELECT COUNT(*) AS total_count
        FROM dbo.candidate_applications
        WHERE requisition_id = :requisition_id
        AND application_status = N'active';
        """
    )
    with engine.connect() as connection:
        return int(connection.execute(query, {"requisition_id": requisition_id}).scalar_one())


def _replace_requisition_skills(connection, requisition_id: int, must_have_skills: list[str], good_to_have_skills: list[str]) -> None:
    connection.execute(
        text("DELETE FROM dbo.requisition_skill_requirements WHERE requisition_id = :requisition_id;"),
        {"requisition_id": requisition_id},
    )
    entries = [
        *[
            {"skill_name": name, "skill_type": "must-have", "priority_order": index + 1}
            for index, name in enumerate(must_have_skills)
        ],
        *[
            {"skill_name": name, "skill_type": "good-to-have", "priority_order": index + 1}
            for index, name in enumerate(good_to_have_skills)
        ],
    ]
    insert_query = text(
        """
        INSERT INTO dbo.requisition_skill_requirements (
          requisition_id,
          skill_name,
          skill_type,
          priority_order
        )
        VALUES (
          :requisition_id,
          :skill_name,
          :skill_type,
          :priority_order
        );
        """
    )
    for entry in entries:
        connection.execute(insert_query, {"requisition_id": requisition_id, **entry})


def create_requisition(engine: Engine, payload: RequisitionCreate) -> RequisitionRecord:
    query = text(
        """
        INSERT INTO dbo.requisitions (
          branch_id,
          hiring_type,
          client_company_id,
          title,
          owner_user_id,
          priority,
          status,
          open_positions,
          target_close_date,
          client_round_required,
          job_description,
          important_notes
        )
        OUTPUT INSERTED.id
        VALUES (
          :location_id,
          CASE WHEN :client_id IS NULL THEN N'internal' ELSE N'external' END,
          :client_id,
          :title,
          :primary_owner_user_id,
          :priority,
          N'open',
          :open_positions,
          :target_close_date,
          :client_round_required,
          :job_description,
          :preferred_update_time_text
        );
        """
    )
    with engine.begin() as connection:
        requisition_id = connection.execute(
            query,
            {
                "location_id": payload.location_id,
                "client_id": payload.client_id,
                "primary_contact_id": payload.primary_contact_id,
                "secondary_contact_id": payload.secondary_contact_id,
                "title": payload.title,
                "primary_owner_user_id": payload.primary_owner_user_id,
                "delivery_owner_user_id": payload.delivery_owner_user_id,
                "priority": payload.priority,
                "open_positions": payload.openings_count,
                "target_close_date": payload.target_closure_date,
                "client_round_required": 1 if payload.client_round_required else 0,
                "job_description": payload.job_description,
                "acceptable_career_gap_months": payload.acceptable_career_gap_months,
                "preferred_update_time_text": payload.profile_update_window_text,
                "created_by_user_id": payload.created_by_user_id,
                "employment_type": payload.employment_type,
                "work_mode": payload.work_mode,
                "pipeline_template_id": payload.stage_template_id,
            },
        ).scalar_one()
        _replace_requisition_skills(connection, int(requisition_id), payload.must_have_skills, payload.good_to_have_skills)
    created = find_requisition_by_id(engine, int(requisition_id))
    if created is None:
        raise RuntimeError("Created requisition could not be reloaded")
    return created


def update_requisition(engine: Engine, requisition_id: int, payload: RequisitionUpdate) -> RequisitionRecord:
    existing = find_requisition_by_id(engine, requisition_id)
    if existing is None:
        raise RuntimeError("Existing requisition could not be loaded")
    query = text(
        """
        UPDATE dbo.requisitions
        SET
          title = COALESCE(:title, title),
          owner_user_id = COALESCE(:primary_owner_user_id, owner_user_id),
          open_positions = COALESCE(:open_positions, open_positions),
          priority = COALESCE(:priority, priority),
          target_close_date = COALESCE(:target_close_date, target_close_date),
          client_round_required = COALESCE(:client_round_required, client_round_required),
          job_description = COALESCE(:job_description, job_description),
          important_notes = CASE
            WHEN :has_preferred_update_time_text = 1 THEN :preferred_update_time_text
            ELSE important_notes
          END,
          updated_at = SYSUTCDATETIME()
        WHERE id = :requisition_id;
        """
    )
    with engine.begin() as connection:
        connection.execute(
            query,
            {
                "requisition_id": requisition_id,
                "has_primary_contact_id": 1 if "primary_contact_id" in payload.model_fields_set else 0,
                "primary_contact_id": payload.primary_contact_id,
                "has_secondary_contact_id": 1 if "secondary_contact_id" in payload.model_fields_set else 0,
                "secondary_contact_id": payload.secondary_contact_id,
                "title": payload.title,
                "primary_owner_user_id": payload.primary_owner_user_id,
                "has_delivery_owner_user_id": 1 if "delivery_owner_user_id" in payload.model_fields_set else 0,
                "delivery_owner_user_id": payload.delivery_owner_user_id,
                "open_positions": payload.openings_count,
                "priority": payload.priority,
                "target_close_date": payload.target_closure_date,
                "has_employment_type": 1 if "employment_type" in payload.model_fields_set else 0,
                "employment_type": payload.employment_type,
                "has_work_mode": 1 if "work_mode" in payload.model_fields_set else 0,
                "work_mode": payload.work_mode,
                "has_acceptable_career_gap_months": 1 if "acceptable_career_gap_months" in payload.model_fields_set else 0,
                "acceptable_career_gap_months": payload.acceptable_career_gap_months,
                "has_preferred_update_time_text": 1 if "profile_update_window_text" in payload.model_fields_set else 0,
                "preferred_update_time_text": payload.profile_update_window_text,
                "client_round_required": payload.client_round_required,
                "job_description": payload.job_description,
                "has_pipeline_template_id": 1 if "stage_template_id" in payload.model_fields_set else 0,
                "pipeline_template_id": payload.stage_template_id,
            },
        )
        if "must_have_skills" in payload.model_fields_set or "good_to_have_skills" in payload.model_fields_set:
            must_have = payload.must_have_skills if payload.must_have_skills is not None else existing.must_have_skills
            good_to_have = payload.good_to_have_skills if payload.good_to_have_skills is not None else existing.good_to_have_skills
            _replace_requisition_skills(connection, requisition_id, must_have, good_to_have)
    updated = find_requisition_by_id(engine, requisition_id)
    if updated is None:
        raise RuntimeError("Updated requisition could not be reloaded")
    return updated


def update_requisition_status(engine: Engine, requisition_id: int, payload: RequisitionStatusUpdate) -> RequisitionRecord:
    query = text(
        """
        UPDATE dbo.requisitions
        SET
          status = :status,
          updated_at = SYSUTCDATETIME()
        WHERE id = :requisition_id;
        """
    )
    with engine.begin() as connection:
        connection.execute(query, {"requisition_id": requisition_id, "status": payload.status})
    updated = find_requisition_by_id(engine, requisition_id)
    if updated is None:
        raise RuntimeError("Updated requisition status could not be reloaded")
    return updated


def list_requisition_assignments(engine: Engine, requisition_id: int) -> list[RequisitionAssignmentRecord]:
    query = text(
        """
        SELECT
          a.id,
          a.location_id,
          a.requisition_id,
          a.assigned_user_id,
          u.full_name AS assigned_user_name,
          a.assignment_type,
          a.assigned_by_user_id,
          au.full_name AS assigned_by_user_name,
          a.assigned_at,
          a.status,
          a.created_at,
          a.updated_at
        FROM dbo.requisition_assignments AS a
        LEFT JOIN dbo.users AS u ON u.id = a.assigned_user_id
        LEFT JOIN dbo.users AS au ON au.id = a.assigned_by_user_id
        WHERE a.requisition_id = :requisition_id
        AND a.status = N'active'
        ORDER BY a.assigned_at DESC, a.id DESC;
        """
    )
    with engine.connect() as connection:
        rows = connection.execute(query, {"requisition_id": requisition_id}).mappings().all()
    return [_map_assignment(row) for row in rows]


def find_requisition_assignment_by_id(engine: Engine, assignment_id: int) -> RequisitionAssignmentRecord | None:
    query = text(
        """
        SELECT
          a.id,
          a.location_id,
          a.requisition_id,
          a.assigned_user_id,
          u.full_name AS assigned_user_name,
          a.assignment_type,
          a.assigned_by_user_id,
          au.full_name AS assigned_by_user_name,
          a.assigned_at,
          a.status,
          a.created_at,
          a.updated_at
        FROM dbo.requisition_assignments AS a
        LEFT JOIN dbo.users AS u ON u.id = a.assigned_user_id
        LEFT JOIN dbo.users AS au ON au.id = a.assigned_by_user_id
        WHERE a.id = :assignment_id;
        """
    )
    with engine.connect() as connection:
        row = connection.execute(query, {"assignment_id": assignment_id}).mappings().first()
    return _map_assignment(row) if row else None


def create_requisition_assignment(
    engine: Engine,
    location_id: int,
    requisition_id: int,
    payload: RequisitionAssignmentCreate,
) -> RequisitionAssignmentRecord:
    insert_query = text(
        """
        INSERT INTO dbo.requisition_assignments (
          location_id,
          requisition_id,
          assigned_user_id,
          assignment_type,
          assigned_by_user_id,
          assigned_at,
          status
        )
        OUTPUT INSERTED.id
        VALUES (
          :location_id,
          :requisition_id,
          :assigned_user_id,
          :assignment_type,
          :assigned_by_user_id,
          SYSUTCDATETIME(),
          N'active'
        );
        """
    )
    with engine.begin() as connection:
        assignment_id = connection.execute(
            insert_query,
            {
                "location_id": location_id,
                "requisition_id": requisition_id,
                "assigned_user_id": payload.assigned_user_id,
                "assignment_type": payload.assignment_type,
                "assigned_by_user_id": payload.assigned_by_user_id or payload.assigned_user_id,
            },
        ).scalar_one()
        if payload.assignment_type == "primary_owner":
            connection.execute(
                text(
                    """
                    UPDATE dbo.requisitions
                    SET owner_user_id = :assigned_user_id, updated_at = SYSUTCDATETIME()
                    WHERE id = :requisition_id;
                    """
                ),
                {"requisition_id": requisition_id, "assigned_user_id": payload.assigned_user_id},
            )
    created = find_requisition_assignment_by_id(engine, int(assignment_id))
    if created is None:
        raise RuntimeError("Created requisition assignment could not be reloaded")
    return created


def remove_requisition_assignment(engine: Engine, assignment_id: int) -> None:
    query = text(
        """
        UPDATE dbo.requisition_assignments
        SET status = N'inactive', updated_at = SYSUTCDATETIME()
        WHERE id = :assignment_id;
        """
    )
    with engine.begin() as connection:
        connection.execute(query, {"assignment_id": assignment_id})

