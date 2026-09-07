from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import Engine, text

from app.schemas.pipeline import PipelineBoardFilters, PipelineStageMove


@dataclass
class PipelineBoardRecord:
    application_id: int
    candidate_id: int
    candidate_name: str
    requisition_id: int
    requisition_title: str
    location_id: int
    location_name: str | None
    owner_user_id: int
    owner_name: str | None
    sourced_by_user_id: int | None
    sourced_by_name: str | None
    current_stage: str
    application_status: str
    stage_updated_at: object
    last_activity_at: object
    expected_joining_date: object


@dataclass
class PipelineApplicationDetailRecord:
    application_id: int
    candidate_id: int
    candidate_name: str
    requisition_id: int
    requisition_title: str
    location_id: int
    location_name: str | None
    owner_user_id: int
    owner_name: str | None
    sourced_by_user_id: int | None
    sourced_by_name: str | None
    submitted_by_user_id: int | None
    submitted_by_name: str | None
    current_stage: str
    application_status: str
    screening_status: str
    stage_reason: str | None
    rejection_side: str
    rejection_stage: str | None
    rejection_reason: str | None
    client_feedback_status: str | None
    client_feedback_notes: str | None
    stage_updated_at: object
    last_activity_at: object
    expected_joining_date: object
    applied_at: object
    updated_at: object


@dataclass
class PipelineHistoryRecord:
    id: int
    candidate_application_id: int
    from_stage: str | None
    to_stage: str
    change_reason: str | None
    changed_by_user_id: int
    changed_by_name: str | None
    changed_at: object
    source_type: str


@dataclass
class PipelineTemplateStageRecord:
    pipeline_template_id: int
    stage_code: str
    stage_order: int
    stage_type: str
    allows_rejection: bool


def list_pipeline_board(engine: Engine, filters: PipelineBoardFilters) -> list[PipelineBoardRecord]:
    query = text(
        """
        SELECT
          ca.id AS application_id,
          c.id AS candidate_id,
          c.full_name AS candidate_name,
          r.id AS requisition_id,
          r.title AS requisition_title,
          r.branch_id AS location_id,
          l.name AS location_name,
          ca.owner_user_id,
          owner_user.full_name AS owner_name,
          c.created_by_user_id AS sourced_by_user_id,
          source_owner.full_name AS sourced_by_name,
          ca.current_stage,
          ca.application_status,
          ca.stage_updated_at,
          ca.updated_at AS last_activity_at,
          ca.expected_joining_date
        FROM dbo.candidate_applications AS ca
        INNER JOIN dbo.candidates AS c
          ON c.id = ca.candidate_id
        INNER JOIN dbo.requisitions AS r
          ON r.id = ca.requisition_id
        LEFT JOIN dbo.branches AS l
          ON l.id = r.branch_id
        LEFT JOIN dbo.users AS owner_user
          ON owner_user.id = ca.owner_user_id
        LEFT JOIN dbo.users AS source_owner
          ON source_owner.id = c.created_by_user_id
        WHERE (:requisition_id IS NULL OR ca.requisition_id = :requisition_id)
        AND (:owner_user_id IS NULL OR ca.owner_user_id = :owner_user_id)
        AND (:sourced_by_user_id IS NULL OR c.created_by_user_id = :sourced_by_user_id)
        AND (:stage IS NULL OR ca.current_stage = :stage)
        AND (:location_id IS NULL OR r.branch_id = :location_id)
        ORDER BY ca.stage_updated_at DESC, ca.id DESC;
        """
    )
    with engine.connect() as connection:
        rows = connection.execute(
            query,
            {
                "requisition_id": filters.requisition_id,
                "owner_user_id": filters.owner_user_id,
                "sourced_by_user_id": filters.sourced_by_user_id,
                "stage": filters.stage,
                "location_id": filters.location_id,
            },
        ).mappings().all()
    return [PipelineBoardRecord(**row) for row in rows]


def find_pipeline_application_by_id(engine: Engine, application_id: int) -> PipelineApplicationDetailRecord | None:
    query = text(
        """
        SELECT TOP 1
          ca.id AS application_id,
          c.id AS candidate_id,
          c.full_name AS candidate_name,
          r.id AS requisition_id,
          r.title AS requisition_title,
          r.branch_id AS location_id,
          l.name AS location_name,
          ca.owner_user_id,
          owner_user.full_name AS owner_name,
          c.created_by_user_id AS sourced_by_user_id,
          source_owner.full_name AS sourced_by_name,
          ca.owner_user_id AS submitted_by_user_id,
          owner_user.full_name AS submitted_by_name,
          ca.current_stage,
          ca.application_status,
          ca.screening_status,
          ca.stage_reason,
          ca.rejection_side,
          ca.rejection_stage,
          ca.rejection_reason,
          ca.client_feedback_status,
          ca.client_feedback_notes,
          ca.stage_updated_at,
          ca.updated_at AS last_activity_at,
          ca.expected_joining_date,
          ca.applied_at,
          ca.updated_at
        FROM dbo.candidate_applications AS ca
        INNER JOIN dbo.candidates AS c
          ON c.id = ca.candidate_id
        INNER JOIN dbo.requisitions AS r
          ON r.id = ca.requisition_id
        LEFT JOIN dbo.branches AS l
          ON l.id = r.branch_id
        LEFT JOIN dbo.users AS owner_user
          ON owner_user.id = ca.owner_user_id
        LEFT JOIN dbo.users AS source_owner
          ON source_owner.id = c.created_by_user_id
        WHERE ca.id = :application_id;
        """
    )
    with engine.connect() as connection:
        row = connection.execute(query, {"application_id": application_id}).mappings().first()
    return PipelineApplicationDetailRecord(**row) if row else None


def find_pipeline_template_stage_for_application(
    engine: Engine,
    application_id: int,
    stage_code: str,
) -> PipelineTemplateStageRecord | None:
    _ = (engine, application_id, stage_code)
    return None


def application_has_pipeline_template(engine: Engine, application_id: int) -> bool:
    _ = (engine, application_id)
    return False


def move_pipeline_stage(engine: Engine, application_id: int, payload: PipelineStageMove) -> tuple[str, PipelineApplicationDetailRecord]:
    before = find_pipeline_application_by_id(engine, application_id)
    if before is None:
        raise RuntimeError("Pipeline application could not be reloaded")
    query = text(
        """
        UPDATE dbo.candidate_applications
        SET
          current_stage = :to_stage,
          stage_reason = CASE WHEN :notes IS NOT NULL THEN :notes ELSE stage_reason END,
          rejection_reason = :rejection_reason,
          rejection_stage = CASE
            WHEN :rejection_reason IS NOT NULL THEN :to_stage
            ELSE rejection_stage
          END,
          rejection_side = CASE
            WHEN :rejection_reason IS NOT NULL AND :to_stage LIKE N'%client%' THEN N'client'
            WHEN :rejection_reason IS NOT NULL THEN N'internal'
            ELSE rejection_side
          END,
          expected_joining_date = COALESCE(:joining_date, expected_joining_date),
          application_status = CASE
            WHEN :to_stage IN (N'rejected', N'client-rejected') THEN N'rejected'
            WHEN :to_stage IN (N'joined', N'hired') THEN N'joined'
            ELSE application_status
          END,
          stage_updated_at = SYSUTCDATETIME(),
          updated_at = SYSUTCDATETIME()
        WHERE id = :application_id;
        """
    )
    history_query = text(
        """
        INSERT INTO dbo.candidate_stage_history (
          candidate_application_id,
          from_stage,
          to_stage,
          change_reason,
          changed_by_user_id,
          changed_at,
          source_type
        )
        VALUES (
          :application_id,
          :from_stage,
          :to_stage,
          :change_reason,
          :changed_by_user_id,
          SYSUTCDATETIME(),
          N'manual'
        );
        """
    )
    with engine.begin() as connection:
        connection.execute(
            query,
            {
                "application_id": application_id,
                "to_stage": payload.to_stage,
                "notes": payload.notes,
                "rejection_reason": payload.rejection_reason,
                "joining_date": payload.joining_date,
            },
        )
        connection.execute(
            history_query,
            {
                "application_id": application_id,
                "from_stage": before.current_stage,
                "to_stage": payload.to_stage,
                "change_reason": payload.notes or payload.rejection_reason,
                "changed_by_user_id": payload.changed_by_user_id or before.owner_user_id,
            },
        )
    after = find_pipeline_application_by_id(engine, application_id)
    if after is None:
        raise RuntimeError("Updated pipeline application could not be reloaded")
    return before.current_stage, after


def list_pipeline_history(engine: Engine, application_id: int) -> list[PipelineHistoryRecord]:
    query = text(
        """
        SELECT
          csh.id,
          csh.candidate_application_id,
          csh.from_stage,
          csh.to_stage,
          csh.change_reason,
          csh.changed_by_user_id,
          u.full_name AS changed_by_name,
          csh.changed_at,
          csh.source_type
        FROM dbo.candidate_stage_history AS csh
        LEFT JOIN dbo.users AS u
          ON u.id = csh.changed_by_user_id
        WHERE csh.candidate_application_id = :application_id
        ORDER BY csh.changed_at DESC, csh.id DESC;
        """
    )
    with engine.connect() as connection:
        rows = connection.execute(query, {"application_id": application_id}).mappings().all()
    return [PipelineHistoryRecord(**row) for row in rows]
