from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import Engine, text

from app.schemas.interview import InterviewCreate, InterviewFeedbackUpdate, InterviewListFilters


@dataclass
class InterviewRecord:
    id: int
    candidate_application_id: int
    candidate_id: int
    candidate_name: str
    requisition_id: int
    requisition_title: str
    location_id: int
    location_name: str | None
    round_type: str
    round_name: str
    scheduled_at: object | None
    interviewer_name: str | None
    interviewer_user_id: int | None
    status: str
    feedback_status: str | None
    decision: str | None
    feedback_notes: str | None
    created_by_user_id: int
    created_by_name: str | None
    created_at: object
    updated_at: object


def _interview_select_sql() -> str:
    return """
        SELECT
          ir.id,
          ir.candidate_application_id,
          c.id AS candidate_id,
          c.full_name AS candidate_name,
          r.id AS requisition_id,
          r.title AS requisition_title,
          r.branch_id AS location_id,
          l.name AS location_name,
          LOWER(ir.round_type) AS round_type,
          ir.round_name,
          ir.scheduled_at,
          ir.interviewer_name,
          ir.interviewer_user_id,
          LOWER(ir.status) AS status,
          LOWER(ir.feedback_status) AS feedback_status,
          LOWER(ir.decision) AS decision,
          ir.feedback_notes,
          ir.created_by_user_id,
          creator.full_name AS created_by_name,
          ir.created_at,
          ir.updated_at
        FROM dbo.interview_rounds AS ir
        INNER JOIN dbo.candidate_applications AS ca
          ON ca.id = ir.candidate_application_id
        INNER JOIN dbo.candidates AS c
          ON c.id = ca.candidate_id
        INNER JOIN dbo.requisitions AS r
          ON r.id = ca.requisition_id
        LEFT JOIN dbo.branches AS l
          ON l.id = r.branch_id
        LEFT JOIN dbo.users AS creator
          ON creator.id = ir.created_by_user_id
    """


def list_interviews(engine: Engine, filters: InterviewListFilters) -> tuple[list[InterviewRecord], int]:
    where = [
        "(:candidate_application_id IS NULL OR candidate_application_id = :candidate_application_id)",
        "(:location_id IS NULL OR location_id = :location_id)",
        "(:tenant_id IS NULL OR location_id IN (SELECT tb.id FROM dbo.branches AS tb WHERE tb.tenant_id = :tenant_id))",
        "(:interviewer_user_id IS NULL OR interviewer_user_id = :interviewer_user_id)",
        "(:status IS NULL OR status = :status)",
    ]
    offset = (filters.page - 1) * filters.page_size
    query = text(
        f"""
        WITH filtered_interviews AS (
          {_interview_select_sql()}
        )
        SELECT *, COUNT(*) OVER() AS total_count
        FROM filtered_interviews
        WHERE {" AND ".join(where)}
        ORDER BY scheduled_at DESC, id DESC
        OFFSET :offset ROWS FETCH NEXT :page_size ROWS ONLY;
        """
    )
    with engine.connect() as connection:
        rows = connection.execute(
            query,
            {
                "candidate_application_id": filters.candidate_application_id,
                "location_id": filters.location_id,
                "tenant_id": filters.tenant_id,
                "interviewer_user_id": filters.interviewer_user_id,
                "status": filters.status,
                "offset": offset,
                "page_size": filters.page_size,
            },
        ).mappings().all()
    total = int(rows[0]["total_count"]) if rows else 0
    return [InterviewRecord(**{key: value for key, value in row.items() if key != "total_count"}) for row in rows], total


def find_interview_by_id(engine: Engine, interview_id: int) -> InterviewRecord | None:
    query = text(
        f"""
        WITH interview_detail AS (
          {_interview_select_sql()}
        )
        SELECT TOP 1 *
        FROM interview_detail
        WHERE id = :interview_id;
        """
    )
    with engine.connect() as connection:
        row = connection.execute(query, {"interview_id": interview_id}).mappings().first()
    return InterviewRecord(**row) if row else None


def create_interview(engine: Engine, payload: InterviewCreate) -> InterviewRecord:
    query = text(
        """
        INSERT INTO dbo.interview_rounds (
          candidate_application_id,
          round_type,
          round_name,
          scheduled_at,
          interviewer_name,
          interviewer_user_id,
          status,
          feedback_status,
          created_by_user_id
        )
        OUTPUT inserted.id
        VALUES (
          :candidate_application_id,
          :round_type,
          :round_name,
          :scheduled_at,
          :interviewer_name,
          :interviewer_user_id,
          :status,
          N'pending',
          :created_by_user_id
        );
        """
    )
    with engine.begin() as connection:
        interview_id = connection.execute(query, payload.model_dump()).scalar_one()
    created = find_interview_by_id(engine, int(interview_id))
    if created is None:
        raise RuntimeError("Created interview could not be reloaded")
    return created


def update_interview_feedback(engine: Engine, interview_id: int, payload: InterviewFeedbackUpdate) -> InterviewRecord:
    query = text(
        """
        UPDATE dbo.interview_rounds
        SET
          status = :status,
          feedback_status = :feedback_status,
          decision = :decision,
          feedback_notes = :feedback_notes,
          updated_at = SYSUTCDATETIME()
        WHERE id = :interview_id;
        """
    )
    with engine.begin() as connection:
        connection.execute(query, {**payload.model_dump(), "interview_id": interview_id})
    updated = find_interview_by_id(engine, interview_id)
    if updated is None:
        raise RuntimeError("Updated interview could not be reloaded")
    return updated
