from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import Engine, text
from sqlalchemy.engine import RowMapping

from app.schemas.approval import ApprovalCreate, ApprovalDecision, ApprovalListFilters


@dataclass
class ApprovalRecord:
    id: int
    location_id: int
    location_name: str | None
    approval_type: str
    related_entity_type: str
    related_entity_id: int
    title: str
    description: str | None
    priority: str
    status: str
    requester_user_id: int
    requester_name: str | None
    assigned_reviewer_user_id: int | None
    assigned_reviewer_name: str | None
    decision_user_id: int | None
    decision_user_name: str | None
    decision_at: object | None
    decision_notes: str | None
    sla_deadline: object | None
    created_at: object
    updated_at: object


def _map_approval(row: RowMapping) -> ApprovalRecord:
    return ApprovalRecord(
        id=row["id"],
        location_id=row["location_id"],
        location_name=row["location_name"],
        approval_type=row["approval_type"],
        related_entity_type=row["related_entity_type"],
        related_entity_id=row["related_entity_id"],
        title=row["title"],
        description=row["description"],
        priority=row["priority"],
        status=row["status"],
        requester_user_id=row["requester_user_id"],
        requester_name=row["requester_name"],
        assigned_reviewer_user_id=row["assigned_reviewer_user_id"],
        assigned_reviewer_name=row["assigned_reviewer_name"],
        decision_user_id=row["decision_user_id"],
        decision_user_name=row["decision_user_name"],
        decision_at=row["decision_at"],
        decision_notes=row["decision_notes"],
        sla_deadline=row["sla_deadline"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _approval_select_sql() -> str:
    return """
      SELECT
        a.id,
        a.location_id,
        l.name AS location_name,
        a.approval_type,
        a.related_entity_type,
        a.related_entity_id,
        a.title,
        a.description,
        a.priority,
        a.status,
        a.requester_user_id,
        requester.full_name AS requester_name,
        a.assigned_reviewer_user_id,
        reviewer.full_name AS assigned_reviewer_name,
        a.decision_user_id,
        decision_user.full_name AS decision_user_name,
        a.decision_at,
        a.decision_notes,
        a.sla_deadline,
        a.created_at,
        a.updated_at
      FROM dbo.approvals AS a
      LEFT JOIN dbo.locations AS l
        ON l.id = a.location_id
      LEFT JOIN dbo.users AS requester
        ON requester.id = a.requester_user_id
      LEFT JOIN dbo.users AS reviewer
        ON reviewer.id = a.assigned_reviewer_user_id
      LEFT JOIN dbo.users AS decision_user
        ON decision_user.id = a.decision_user_id
    """


def list_approvals(engine: Engine, filters: ApprovalListFilters) -> tuple[list[ApprovalRecord], int]:
    query = text(
        f"""
        WITH filtered_approvals AS (
          {_approval_select_sql()}
          WHERE (:location_id IS NULL OR a.location_id = :location_id)
          AND (:tenant_id IS NULL OR a.location_id IN (SELECT tb.id FROM dbo.branches AS tb WHERE tb.tenant_id = :tenant_id))
          AND (:approval_type IS NULL OR a.approval_type = :approval_type)
          AND (:status IS NULL OR a.status = :status)
          AND (:priority IS NULL OR a.priority = :priority)
          AND (:requester_user_id IS NULL OR a.requester_user_id = :requester_user_id)
          AND (:assigned_reviewer_user_id IS NULL OR a.assigned_reviewer_user_id = :assigned_reviewer_user_id)
        )
        SELECT *, COUNT(*) OVER() AS total_count
        FROM filtered_approvals
        ORDER BY
          CASE priority WHEN 'critical' THEN 1 WHEN 'high' THEN 2 ELSE 3 END,
          created_at DESC
        OFFSET :offset ROWS FETCH NEXT :page_size ROWS ONLY;
        """
    )
    with engine.connect() as connection:
        rows = connection.execute(
            query,
            {
                "location_id": filters.location_id,
                "tenant_id": filters.tenant_id,
                "approval_type": filters.approval_type,
                "status": filters.status,
                "priority": filters.priority,
                "requester_user_id": filters.requester_user_id,
                "assigned_reviewer_user_id": filters.assigned_reviewer_user_id,
                "offset": (filters.page - 1) * filters.page_size,
                "page_size": filters.page_size,
            },
        ).mappings().all()
    total = rows[0]["total_count"] if rows else 0
    return [_map_approval(row) for row in rows], total


def find_approval_by_id(engine: Engine, approval_id: int) -> ApprovalRecord | None:
    query = text(f"{_approval_select_sql()} WHERE a.id = :approval_id;")
    with engine.connect() as connection:
        row = connection.execute(query, {"approval_id": approval_id}).mappings().first()
    if row is None:
        return None
    return _map_approval(row)


def create_approval(engine: Engine, payload: ApprovalCreate) -> ApprovalRecord:
    query = text(
        """
        INSERT INTO dbo.approvals (
          location_id, approval_type, related_entity_type, related_entity_id,
          title, description, priority, requester_user_id,
          assigned_reviewer_user_id, sla_deadline
        )
        OUTPUT INSERTED.id
        VALUES (
          :location_id, :approval_type, :related_entity_type, :related_entity_id,
          :title, :description, :priority, :requester_user_id,
          :assigned_reviewer_user_id, :sla_deadline
        );
        """
    )
    with engine.begin() as connection:
        approval_id = connection.execute(query, payload.model_dump()).scalar_one()
    created = find_approval_by_id(engine, int(approval_id))
    if created is None:
        raise RuntimeError("Created approval could not be reloaded")
    return created


def decide_approval(engine: Engine, approval_id: int, payload: ApprovalDecision) -> ApprovalRecord:
    query = text(
        """
        UPDATE dbo.approvals
        SET
          status = :decision,
          decision_user_id = :decision_user_id,
          decision_at = SYSUTCDATETIME(),
          decision_notes = :decision_notes,
          updated_at = SYSUTCDATETIME()
        WHERE id = :approval_id AND status = 'pending';
        """
    )
    with engine.begin() as connection:
        rows_affected = connection.execute(
            query,
            {
                "approval_id": approval_id,
                "decision": payload.decision,
                "decision_user_id": payload.decision_user_id,
                "decision_notes": payload.decision_notes,
            },
        ).rowcount
    if rows_affected == 0:
        raise ValueError("Approval not found or already decided")
    updated = find_approval_by_id(engine, approval_id)
    if updated is None:
        raise RuntimeError("Updated approval could not be reloaded")
    return updated
