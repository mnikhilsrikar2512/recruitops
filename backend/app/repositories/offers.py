from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import Engine, text

from app.schemas.offer import OfferCreate, OfferDecisionUpdate, OfferListFilters


@dataclass
class OfferRecord:
    application_id: int
    candidate_id: int
    candidate_name: str
    candidate_email: str | None
    requisition_id: int
    requisition_title: str
    requisition_code: str | None
    location_id: int
    location_name: str | None
    owner_user_id: int
    owner_name: str | None
    current_stage: str
    application_status: str
    offer_status: str
    offered_ctc: object | None
    offer_currency: str | None
    signing_bonus: object | None
    expected_joining_date: object | None
    offer_notes: str | None
    approval_request_id: int | None
    approval_status: str | None
    requested_by_user_id: int | None
    assigned_to_user_id: int | None
    offer_created_at: object | None
    offer_sent_at: object | None
    updated_at: object


def _offer_select_sql() -> str:
    return """
        SELECT
          ca.id AS application_id,
          c.id AS candidate_id,
          c.full_name AS candidate_name,
          c.email AS candidate_email,
          r.id AS requisition_id,
          r.title AS requisition_title,
          r.requisition_code,
          r.branch_id AS location_id,
          l.name AS location_name,
          ca.owner_user_id,
          owner_user.full_name AS owner_name,
          ca.current_stage,
          ca.application_status,
          COALESCE(ca.offer_status, CASE
            WHEN ca.application_status = N'joined' THEN N'accepted'
            WHEN LOWER(ca.current_stage) LIKE N'%offer%' THEN N'pending-approval'
            ELSE N'draft'
          END) AS offer_status,
          ca.offered_ctc,
          ca.offer_currency,
          ca.signing_bonus,
          ca.expected_joining_date,
          ca.offer_notes,
          approval.id AS approval_request_id,
          approval.status AS approval_status,
          approval.requested_by_user_id,
          approval.assigned_to_user_id,
          ca.offer_created_at,
          ca.offer_sent_at,
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
        OUTER APPLY (
          SELECT TOP 1 *
          FROM dbo.approval_requests AS ar
          WHERE ar.source_type = N'offer'
          AND ar.source_id = ca.id
          ORDER BY ar.created_at DESC, ar.id DESC
        ) AS approval
    """


def list_offers(engine: Engine, filters: OfferListFilters) -> tuple[list[OfferRecord], int]:
    where = [
        "(:location_id IS NULL OR location_id = :location_id)",
        "(:tenant_id IS NULL OR location_id IN (SELECT tb.id FROM dbo.branches AS tb WHERE tb.tenant_id = :tenant_id))",
        "(:requisition_id IS NULL OR requisition_id = :requisition_id)",
        "(:status IS NULL OR offer_status = :status)",
        "(offer_created_at IS NOT NULL OR LOWER(current_stage) LIKE N'%offer%' OR application_status = N'joined' OR approval_request_id IS NOT NULL)",
    ]
    query = text(
        f"""
        WITH offer_rows AS (
          {_offer_select_sql()}
        )
        SELECT *, COUNT(*) OVER() AS total_count
        FROM offer_rows
        WHERE {" AND ".join(where)}
        ORDER BY COALESCE(offer_created_at, offer_sent_at, updated_at) DESC, application_id DESC
        OFFSET :offset ROWS FETCH NEXT :page_size ROWS ONLY;
        """
    )
    with engine.connect() as connection:
        rows = connection.execute(
            query,
            {
                "location_id": filters.location_id,
                "tenant_id": filters.tenant_id,
                "requisition_id": filters.requisition_id,
                "status": filters.status,
                "offset": (filters.page - 1) * filters.page_size,
                "page_size": filters.page_size,
            },
        ).mappings().all()
    total = int(rows[0]["total_count"]) if rows else 0
    return [OfferRecord(**{key: value for key, value in row.items() if key != "total_count"}) for row in rows], total


def find_offer_by_application_id(engine: Engine, application_id: int) -> OfferRecord | None:
    query = text(
        f"""
        WITH offer_rows AS (
          {_offer_select_sql()}
        )
        SELECT TOP 1 *
        FROM offer_rows
        WHERE application_id = :application_id;
        """
    )
    with engine.connect() as connection:
        row = connection.execute(query, {"application_id": application_id}).mappings().first()
    return OfferRecord(**row) if row else None


def create_offer(engine: Engine, payload: OfferCreate, *, location_id: int, actor_user_id: int) -> OfferRecord:
    update_query = text(
        """
        UPDATE dbo.candidate_applications
        SET
          current_stage = CASE WHEN LOWER(current_stage) LIKE N'%offer%' THEN current_stage ELSE N'offer' END,
          offer_status = N'pending-approval',
          offered_ctc = :offered_ctc,
          offer_currency = :offer_currency,
          signing_bonus = :signing_bonus,
          expected_joining_date = COALESCE(:expected_joining_date, expected_joining_date),
          offer_notes = :offer_notes,
          offer_created_at = COALESCE(offer_created_at, SYSUTCDATETIME()),
          updated_at = SYSUTCDATETIME()
        WHERE id = :candidate_application_id;
        """
    )
    approval_query = text(
        """
        INSERT INTO dbo.approval_requests (
          location_id,
          request_type,
          source_type,
          source_id,
          requested_by_user_id,
          assigned_to_user_id,
          priority,
          status,
          decision_notes
        )
        VALUES (
          :location_id,
          N'offer-approval',
          N'offer',
          :candidate_application_id,
          :requested_by_user_id,
          :assigned_to_user_id,
          N'high',
          N'pending',
          :offer_notes
        );
        """
    )
    values = payload.model_dump()
    with engine.begin() as connection:
        connection.execute(update_query, values)
        connection.execute(
            approval_query,
            {
                "location_id": location_id,
                "candidate_application_id": payload.candidate_application_id,
                "requested_by_user_id": payload.requested_by_user_id or actor_user_id,
                "assigned_to_user_id": payload.assigned_to_user_id,
                "offer_notes": payload.offer_notes,
            },
        )
    created = find_offer_by_application_id(engine, payload.candidate_application_id)
    if created is None:
        raise RuntimeError("Created offer could not be reloaded")
    return created


def update_offer_decision(engine: Engine, application_id: int, payload: OfferDecisionUpdate, *, actor_user_id: int) -> OfferRecord:
    is_accepted = payload.status == "accepted"
    app_status = "joined" if is_accepted else "active"
    update_query = text(
        """
        UPDATE dbo.candidate_applications
        SET
          offer_status = :offer_status,
          application_status = CASE WHEN :is_accepted = 1 THEN N'joined' ELSE application_status END,
          expected_joining_date = COALESCE(:expected_joining_date, expected_joining_date),
          offer_sent_at = CASE WHEN :offer_status IN (N'sent', N'accepted') THEN COALESCE(offer_sent_at, SYSUTCDATETIME()) ELSE offer_sent_at END,
          stage_reason = COALESCE(:decision_notes, stage_reason),
          updated_at = SYSUTCDATETIME()
        WHERE id = :application_id;
        """
    )
    approval_query = text(
        """
        UPDATE dbo.approval_requests
        SET
          status = CASE
            WHEN :offer_status = N'approved' THEN N'approved'
            WHEN :offer_status = N'declined' THEN N'rejected'
            ELSE status
          END,
          decision = CASE
            WHEN :offer_status IN (N'approved', N'accepted') THEN N'approved'
            WHEN :offer_status = N'declined' THEN N'rejected'
            ELSE decision
          END,
          decision_notes = COALESCE(:decision_notes, decision_notes),
          decided_by_user_id = CASE WHEN :offer_status IN (N'approved', N'declined', N'accepted') THEN :actor_user_id ELSE decided_by_user_id END,
          decided_at = CASE WHEN :offer_status IN (N'approved', N'declined', N'accepted') THEN SYSUTCDATETIME() ELSE decided_at END,
          updated_at = SYSUTCDATETIME()
        WHERE source_type = N'offer'
        AND source_id = :application_id;
        """
    )
    with engine.begin() as connection:
        connection.execute(
            update_query,
            {
                "application_id": application_id,
                "offer_status": payload.status,
                "is_accepted": 1 if is_accepted else 0,
                "expected_joining_date": payload.expected_joining_date,
                "decision_notes": payload.decision_notes,
                "app_status": app_status,
            },
        )
        connection.execute(
            approval_query,
            {
                "application_id": application_id,
                "offer_status": payload.status,
                "decision_notes": payload.decision_notes,
                "actor_user_id": actor_user_id,
            },
        )
    updated = find_offer_by_application_id(engine, application_id)
    if updated is None:
        raise RuntimeError("Updated offer could not be reloaded")
    return updated
