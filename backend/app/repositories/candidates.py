from __future__ import annotations

import json
from dataclasses import dataclass

from sqlalchemy import Engine, text
from sqlalchemy.engine import RowMapping

from app.repositories.display_ids import ENTITY_CANDIDATE, allocate_display_id
from app.schemas.candidate import (
    CandidateCreate,
    CandidateDocumentCreate,
    CandidateFinalizePayload,
    CandidateListFilters,
    CandidateUpdate,
)


@dataclass
class CandidateRecord:
    id: int
    candidate_code: str | None
    branch_code: str | None
    full_name: str
    email: str | None
    phone: str | None
    current_company: str | None
    current_designation: str | None
    source_type: str | None
    source_detail: str | None
    total_experience_years: float | None
    notice_period_days: int | None
    social_profiles_json: str | None
    sourced_by_user_id: int | None
    sourced_by_name: str | None
    primary_owner_user_id: int | None
    primary_owner_name: str | None
    created_by_user_id: int
    duplicate_state: str
    profile_status: str
    intake_stage: str
    resume_file_name: str | None
    resume_file_path: str | None
    resume_uploaded_at: object
    finalized_at: object
    created_at: object
    updated_at: object
    applications_count: int = 0
    linked_requisition_titles: list[str] | None = None


@dataclass
class CandidateApplicationSummaryRecord:
    id: int
    requisition_id: int
    requisition_title: str | None
    location_id: int
    owner_user_id: int
    owner_name: str | None
    submitted_by_user_id: int | None
    current_stage: str
    application_status: str
    stage_updated_at: object
    expected_joining_date: object


@dataclass
class CandidateFootprintEntryRecord:
    """Admin-only cross-tenant footprint entry: WHERE a candidate is in play.

    Deliberately exposes placement context (client, branch, stage, status)
    and NOTHING tenant-private — no notes, no offer terms, no owner
    identities. This is an oversight view, not a data export.
    """

    application_id: int
    requisition_id: int
    requisition_code: str | None
    requisition_title: str | None
    client_id: int | None
    client_name: str | None
    branch_id: int
    branch_code: str | None
    current_stage: str
    application_status: str
    stage_updated_at: object
    applied_at: object


@dataclass
class CandidateDocumentRecord:
    id: int
    candidate_id: int
    document_type: str
    file_name: str
    file_path: str
    verification_status: str
    uploaded_by_user_id: int
    verified_by_user_id: int | None
    verified_at: object
    created_at: object
    updated_at: object


@dataclass
class CandidateDuplicateMatchRecord:
    matched_candidate_id: int
    matched_candidate_name: str
    email: str | None
    phone: str | None
    current_company: str | None
    current_designation: str | None
    duplicate_state: str
    match_score: int
    match_reasons: list[str]


@dataclass
class DuplicateReviewCaseRecord:
    id: int
    candidate_id: int
    matched_candidate_id: int | None
    decision_status: str
    decision_notes: str | None
    requested_by_user_id: int | None
    assigned_reviewer_user_id: int | None
    created_at: object
    updated_at: object


@dataclass
class CandidateFinalizeRecord:
    candidate_id: int
    requisition_id: int
    application_id: int
    current_stage: str
    application_status: str
    finalized_at: object


def _candidate_select_sql() -> str:
    return """
        SELECT
          c.id,
          c.candidate_code,
          cb.code AS branch_code,
          c.full_name,
          c.email,
          c.phone,
          CAST(NULL AS NVARCHAR(150)) AS current_company,
          CAST(NULL AS NVARCHAR(150)) AS current_designation,
          c.source AS source_type,
          c.source_portal AS source_detail,
          c.total_experience_years,
          c.notice_period_days,
          CAST(NULL AS NVARCHAR(MAX)) AS social_profiles_json,
          c.created_by_user_id AS sourced_by_user_id,
          source_owner.full_name AS sourced_by_name,
          c.primary_owner_user_id,
          primary_owner.full_name AS primary_owner_name,
          c.created_by_user_id,
          c.duplicate_check_status AS duplicate_state,
          c.profile_status,
          c.intake_stage,
          c.resume_file_name,
          c.resume_file_path,
          c.resume_uploaded_at,
          c.finalized_at,
          c.created_at,
          c.updated_at,
          COUNT(ca.id) AS applications_count
        FROM dbo.candidates AS c
        LEFT JOIN dbo.branches AS cb
          ON cb.id = c.branch_id
        LEFT JOIN dbo.users AS source_owner
          ON source_owner.id = c.created_by_user_id
        LEFT JOIN dbo.users AS primary_owner
          ON primary_owner.id = c.primary_owner_user_id
        LEFT JOIN dbo.candidate_applications AS ca
          ON ca.candidate_id = c.id
    """


def _map_candidate(row: RowMapping, linked_requisition_titles: list[str] | None = None) -> CandidateRecord:
    return CandidateRecord(
        id=row["id"],
        candidate_code=row["candidate_code"],
        branch_code=row["branch_code"],
        full_name=row["full_name"],
        email=row["email"],
        phone=row["phone"],
        current_company=row["current_company"],
        current_designation=row["current_designation"],
        source_type=row["source_type"],
        source_detail=row["source_detail"],
        total_experience_years=float(row["total_experience_years"]) if row["total_experience_years"] is not None else None,
        notice_period_days=row["notice_period_days"],
        social_profiles_json=row["social_profiles_json"],
        sourced_by_user_id=row["sourced_by_user_id"],
        sourced_by_name=row["sourced_by_name"],
        primary_owner_user_id=row["primary_owner_user_id"],
        primary_owner_name=row["primary_owner_name"],
        created_by_user_id=row["created_by_user_id"],
        duplicate_state=row["duplicate_state"],
        profile_status=row["profile_status"],
        intake_stage=row["intake_stage"],
        resume_file_name=row["resume_file_name"],
        resume_file_path=row["resume_file_path"],
        resume_uploaded_at=row["resume_uploaded_at"],
        finalized_at=row["finalized_at"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        applications_count=row.get("applications_count", 0) or 0,
        linked_requisition_titles=linked_requisition_titles or [],
    )


def _load_linked_requisition_titles(engine: Engine, candidate_ids: list[int]) -> dict[int, list[str]]:
    if not candidate_ids:
        return {}
    bind_names = [f"cid_{i}" for i in range(len(candidate_ids))]
    placeholders = ", ".join(f":{name}" for name in bind_names)
    query = text(
        f"""
        SELECT ca.candidate_id, r.title
        FROM dbo.candidate_applications AS ca
        INNER JOIN dbo.requisitions AS r
          ON r.id = ca.requisition_id
        WHERE ca.candidate_id IN ({placeholders})
        ORDER BY r.title;
        """
    )
    params = {name: cid for name, cid in zip(bind_names, candidate_ids)}
    with engine.connect() as connection:
        rows = connection.execute(query, params).mappings().all()
    items: dict[int, list[str]] = {}
    for row in rows:
        items.setdefault(row["candidate_id"], []).append(row["title"])
    return items


def _parse_social_profiles(value: str | None) -> list[dict]:
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


def list_candidates(engine: Engine, filters: CandidateListFilters) -> tuple[list[CandidateRecord], int]:
    query = text(
        f"""
        WITH filtered_candidates AS (
          {_candidate_select_sql()}
          WHERE (:source_type IS NULL OR c.source = :source_type)
          AND (:duplicate_state IS NULL OR c.duplicate_check_status = :duplicate_state)
          AND (:owner_user_id IS NULL OR c.primary_owner_user_id = :owner_user_id)
          AND (:sourced_by_user_id IS NULL OR c.created_by_user_id = :sourced_by_user_id)
          AND (
            :requisition_id IS NULL
            OR EXISTS (
              SELECT 1
              FROM dbo.candidate_applications AS ca_filter
              WHERE ca_filter.candidate_id = c.id
              AND ca_filter.requisition_id = :requisition_id
            )
          )
          AND (
            :search IS NULL
            OR c.full_name LIKE '%' + :search + '%'
            OR c.email LIKE '%' + :search + '%'
            OR c.phone LIKE '%' + :search + '%'
            OR c.candidate_code LIKE '%' + :search + '%'
            OR cb.code LIKE '%' + :search + '%'
          )
          GROUP BY
            c.id,
            c.candidate_code,
            cb.code,
            c.full_name,
            c.email,
            c.phone,
            c.source,
            c.source_portal,
            c.total_experience_years,
            c.notice_period_days,
            c.created_by_user_id,
            source_owner.full_name,
            c.primary_owner_user_id,
            primary_owner.full_name,
            c.duplicate_check_status,
            c.profile_status,
            c.intake_stage,
            c.resume_file_name,
            c.resume_file_path,
            c.resume_uploaded_at,
            c.finalized_at,
            c.created_at,
            c.updated_at
        )
        SELECT *, COUNT(*) OVER() AS total_count
        FROM filtered_candidates
        ORDER BY updated_at DESC, id DESC
        OFFSET :offset ROWS FETCH NEXT :page_size ROWS ONLY;
        """
    )
    with engine.connect() as connection:
        rows = connection.execute(
            query,
            {
                "source_type": filters.source_type,
                "duplicate_state": filters.duplicate_state,
                "owner_user_id": filters.owner_user_id,
                "sourced_by_user_id": filters.sourced_by_user_id,
                "requisition_id": filters.requisition_id,
                "search": filters.search,
                "offset": (filters.page - 1) * filters.page_size,
                "page_size": filters.page_size,
            },
        ).mappings().all()
    linked_titles = _load_linked_requisition_titles(engine, [row["id"] for row in rows])
    total = rows[0]["total_count"] if rows else 0
    return [_map_candidate(row, linked_titles.get(row["id"], [])) for row in rows], total


def find_candidate_by_id(engine: Engine, candidate_id: int) -> CandidateRecord | None:
    query = text(
        f"""
        SELECT TOP 1 *
        FROM (
          {_candidate_select_sql()}
          WHERE c.id = :candidate_id
          GROUP BY
            c.id,
            c.candidate_code,
            cb.code,
            c.full_name,
            c.email,
            c.phone,
            c.source,
            c.source_portal,
            c.total_experience_years,
            c.notice_period_days,
            c.created_by_user_id,
            source_owner.full_name,
            c.primary_owner_user_id,
            primary_owner.full_name,
            c.duplicate_check_status,
            c.profile_status,
            c.intake_stage,
            c.resume_file_name,
            c.resume_file_path,
            c.resume_uploaded_at,
            c.finalized_at,
            c.created_at,
            c.updated_at
        ) AS selected_candidates;
        """
    )
    with engine.connect() as connection:
        row = connection.execute(query, {"candidate_id": candidate_id}).mappings().first()
    if not row:
        return None
    linked_titles = _load_linked_requisition_titles(engine, [candidate_id])
    return _map_candidate(row, linked_titles.get(candidate_id, []))


def get_candidate_footprint(engine: Engine, candidate_id: int) -> list[CandidateFootprintEntryRecord]:
    """Cross-tenant footprint for one candidate (admin oversight only).

    One row per application across ALL tenants: which client company the
    candidate is in play with, on which branch, and the coarse pipeline
    position. Tenant-private fields (notes, offer terms, owner identities)
    are intentionally not selected.
    """
    query = text(
        """
        SELECT
          ca.id AS application_id,
          ca.requisition_id,
          r.requisition_code,
          r.title AS requisition_title,
          r.client_company_id AS client_id,
          cc.name AS client_name,
          r.branch_id AS branch_id,
          b.code AS branch_code,
          ca.current_stage,
          ca.application_status,
          ca.stage_updated_at,
          ca.applied_at
        FROM dbo.candidate_applications AS ca
        INNER JOIN dbo.requisitions AS r
          ON r.id = ca.requisition_id
        LEFT JOIN dbo.client_companies AS cc
          ON cc.id = r.client_company_id
        LEFT JOIN dbo.branches AS b
          ON b.id = r.branch_id
        WHERE ca.candidate_id = :candidate_id
        ORDER BY ca.applied_at DESC, ca.id DESC;
        """
    )
    with engine.connect() as connection:
        rows = connection.execute(query, {"candidate_id": candidate_id}).mappings().all()
    return [
        CandidateFootprintEntryRecord(
            application_id=int(row["application_id"]),
            requisition_id=int(row["requisition_id"]),
            requisition_code=row["requisition_code"],
            requisition_title=row["requisition_title"],
            client_id=(int(row["client_id"]) if row["client_id"] is not None else None),
            client_name=row["client_name"],
            branch_id=int(row["branch_id"]) if row["branch_id"] is not None else 0,
            branch_code=row["branch_code"],
            current_stage=row["current_stage"],
            application_status=row["application_status"],
            stage_updated_at=row["stage_updated_at"],
            applied_at=row["applied_at"],
        )
        for row in rows
    ]


def list_candidate_applications(engine: Engine, candidate_id: int) -> list[CandidateApplicationSummaryRecord]:
    query = text(
        """
        SELECT
          ca.id,
          ca.requisition_id,
          r.title AS requisition_title,
          r.branch_id AS location_id,
          ca.owner_user_id,
          owner_user.full_name AS owner_name,
          ca.owner_user_id AS submitted_by_user_id,
          ca.current_stage,
          ca.application_status,
          ca.stage_updated_at,
          ca.expected_joining_date
        FROM dbo.candidate_applications AS ca
        INNER JOIN dbo.requisitions AS r
          ON r.id = ca.requisition_id
        LEFT JOIN dbo.users AS owner_user
          ON owner_user.id = ca.owner_user_id
        WHERE ca.candidate_id = :candidate_id
        ORDER BY ca.stage_updated_at DESC, ca.id DESC;
        """
    )
    with engine.connect() as connection:
        rows = connection.execute(query, {"candidate_id": candidate_id}).mappings().all()
    return [
        CandidateApplicationSummaryRecord(
            id=row["id"],
            requisition_id=row["requisition_id"],
            requisition_title=row["requisition_title"],
            location_id=row["location_id"],
            owner_user_id=row["owner_user_id"],
            owner_name=row["owner_name"],
            submitted_by_user_id=row["submitted_by_user_id"],
            current_stage=row["current_stage"],
            application_status=row["application_status"],
            stage_updated_at=row["stage_updated_at"],
            expected_joining_date=row["expected_joining_date"],
        )
        for row in rows
    ]


def count_active_candidate_applications(engine: Engine, candidate_id: int) -> int:
    query = text(
        """
        SELECT COUNT(*) AS total_count
        FROM dbo.candidate_applications
        WHERE candidate_id = :candidate_id
        AND application_status = N'active';
        """
    )
    with engine.connect() as connection:
        return int(connection.execute(query, {"candidate_id": candidate_id}).scalar_one())


def count_candidate_applications_for_requisition(engine: Engine, candidate_id: int, requisition_id: int) -> int:
    query = text(
        """
        SELECT COUNT(*) AS total_count
        FROM dbo.candidate_applications
        WHERE candidate_id = :candidate_id
        AND requisition_id = :requisition_id
        AND application_status IN (N'active', N'joined', N'offered');
        """
    )
    with engine.connect() as connection:
        return int(
            connection.execute(
                query,
                {"candidate_id": candidate_id, "requisition_id": requisition_id},
            ).scalar_one()
        )


def create_candidate(engine: Engine, payload: CandidateCreate) -> CandidateRecord:
    query = text(
        """
        INSERT INTO dbo.candidates (
          branch_id,
          candidate_code,
          full_name,
          email,
          phone,
          source,
          source_portal,
          total_experience_years,
          notice_period_days,
          created_by_user_id,
          primary_owner_user_id,
          profile_status,
          intake_stage,
          status,
          resume_parsing_status,
          duplicate_check_status
        )
        OUTPUT INSERTED.id
        VALUES (
          (SELECT u.location_id FROM dbo.users AS u WHERE u.id = :branch_owner_user_id),
          :candidate_code,
          :full_name,
          :email,
          :phone,
          :source,
          :source_detail,
          :total_experience_years,
          :notice_period_days,
          :created_by_user_id,
          :primary_owner_user_id,
          :profile_status,
          :intake_stage,
          N'active',
          N'pending',
          N'not-started'
        );
        """
    )
    with engine.begin() as connection:
        creator_user_id = payload.created_by_user_id or payload.primary_owner_user_id
        creator_branch_id = connection.execute(
            text("SELECT location_id FROM dbo.users WHERE id = :user_id;"),
            {"user_id": creator_user_id},
        ).scalar_one_or_none()
        candidate_code = (
            allocate_display_id(connection, ENTITY_CANDIDATE, int(creator_branch_id))
            if creator_branch_id is not None
            else None
        )
        candidate_id = connection.execute(
            query,
            {
                "branch_owner_user_id": creator_user_id,
                "candidate_code": candidate_code,
                "full_name": payload.full_name,
                "email": payload.email,
                "phone": payload.phone,
                "source": payload.source_type,
                "source_type": payload.source_type,
                "source_detail": payload.source_detail,
                "current_company": payload.current_company,
                "current_designation": payload.current_designation,
                "total_experience_years": payload.total_experience_years,
                "notice_period_days": payload.notice_period_days,
                "social_profiles_json": json.dumps([item.model_dump() for item in payload.social_profiles]),
                "sourced_by_user_id": payload.sourced_by_user_id or payload.created_by_user_id,
                "primary_owner_user_id": payload.primary_owner_user_id,
                "created_by_user_id": payload.created_by_user_id or payload.primary_owner_user_id,
                "profile_status": "draft" if payload.save_mode == "draft" else "active",
                "intake_stage": "uploaded" if payload.save_mode == "draft" else "ready-to-save",
            },
        ).scalar_one()
    created = find_candidate_by_id(engine, int(candidate_id))
    if created is None:
        raise RuntimeError("Created candidate could not be reloaded")
    return created


def update_candidate(engine: Engine, candidate_id: int, payload: CandidateUpdate) -> CandidateRecord:
    query = text(
        """
        UPDATE dbo.candidates
        SET
          full_name = COALESCE(:full_name, full_name),
          email = CASE WHEN :has_email = 1 THEN :email ELSE email END,
          phone = CASE WHEN :has_phone = 1 THEN :phone ELSE phone END,
          source = COALESCE(:source_type, source),
          source_portal = CASE WHEN :has_source_detail = 1 THEN :source_detail ELSE source_portal END,
          total_experience_years = CASE WHEN :has_total_experience_years = 1 THEN :total_experience_years ELSE total_experience_years END,
          notice_period_days = CASE WHEN :has_notice_period_days = 1 THEN :notice_period_days ELSE notice_period_days END,
          created_by_user_id = CASE WHEN :has_sourced_by_user_id = 1 THEN :sourced_by_user_id ELSE created_by_user_id END,
          primary_owner_user_id = CASE WHEN :has_primary_owner_user_id = 1 THEN :primary_owner_user_id ELSE primary_owner_user_id END,
          updated_at = SYSUTCDATETIME()
        WHERE id = :candidate_id;
        """
    )
    with engine.begin() as connection:
        connection.execute(
            query,
            {
                "candidate_id": candidate_id,
                "full_name": payload.full_name,
                "has_email": 1 if "email" in payload.model_fields_set else 0,
                "email": payload.email,
                "has_phone": 1 if "phone" in payload.model_fields_set else 0,
                "phone": payload.phone,
                "source_type": payload.source_type,
                "has_source_detail": 1 if "source_detail" in payload.model_fields_set else 0,
                "source_detail": payload.source_detail,
                "has_current_company": 1 if "current_company" in payload.model_fields_set else 0,
                "current_company": payload.current_company,
                "has_current_designation": 1 if "current_designation" in payload.model_fields_set else 0,
                "current_designation": payload.current_designation,
                "has_total_experience_years": 1 if "total_experience_years" in payload.model_fields_set else 0,
                "total_experience_years": payload.total_experience_years,
                "has_notice_period_days": 1 if "notice_period_days" in payload.model_fields_set else 0,
                "notice_period_days": payload.notice_period_days,
                "has_social_profiles": 1 if "social_profiles" in payload.model_fields_set else 0,
                "social_profiles_json": json.dumps([item.model_dump() for item in payload.social_profiles or []]),
                "has_sourced_by_user_id": 1 if "sourced_by_user_id" in payload.model_fields_set else 0,
                "sourced_by_user_id": payload.sourced_by_user_id,
                "has_primary_owner_user_id": 1 if "primary_owner_user_id" in payload.model_fields_set else 0,
                "primary_owner_user_id": payload.primary_owner_user_id,
            },
        )
    updated = find_candidate_by_id(engine, candidate_id)
    if updated is None:
        raise RuntimeError("Updated candidate could not be reloaded")
    return updated


def create_candidate_document(engine: Engine, candidate_id: int, payload: CandidateDocumentCreate) -> CandidateDocumentRecord:
    query = text(
        """
        INSERT INTO dbo.candidate_documents (
          candidate_id,
          document_type,
          file_name,
          file_path,
          verification_status,
          uploaded_by_user_id
        )
        OUTPUT INSERTED.id
        VALUES (
          :candidate_id,
          :document_type,
          :file_name,
          :file_path,
          :verification_status,
          :uploaded_by_user_id
        );
        """
    )
    with engine.begin() as connection:
        document_id = connection.execute(
            query,
            {
                "candidate_id": candidate_id,
                "document_type": payload.document_type,
                "file_name": payload.file_name,
                "file_path": payload.file_path,
                "verification_status": payload.verification_status,
                "uploaded_by_user_id": payload.uploaded_by_user_id,
            },
        ).scalar_one()
    return find_candidate_document_by_id(engine, int(document_id))


def find_candidate_document_by_id(engine: Engine, document_id: int) -> CandidateDocumentRecord:
    query = text(
        """
        SELECT TOP 1
          id,
          candidate_id,
          document_type,
          file_name,
          file_path,
          verification_status,
          uploaded_by_user_id,
          verified_by_user_id,
          verified_at,
          created_at,
          updated_at
        FROM dbo.candidate_documents
        WHERE id = :document_id;
        """
    )
    with engine.connect() as connection:
        row = connection.execute(query, {"document_id": document_id}).mappings().first()
    if row is None:
        raise RuntimeError("Candidate document could not be reloaded")
    return CandidateDocumentRecord(**row)


def find_duplicate_matches(engine: Engine, candidate_id: int) -> list[CandidateDuplicateMatchRecord]:
    query = text(
        """
        SELECT
          existing.id AS matched_candidate_id,
          existing.full_name AS matched_candidate_name,
          existing.email,
          existing.phone,
          CAST(NULL AS NVARCHAR(150)) AS current_company,
          CAST(NULL AS NVARCHAR(150)) AS current_designation,
          existing.duplicate_check_status AS duplicate_state,
          current_candidate.email AS current_email,
          current_candidate.phone AS current_phone,
          current_candidate.full_name AS current_name
        FROM dbo.candidates AS current_candidate
        INNER JOIN dbo.candidates AS existing
          ON existing.id <> current_candidate.id
         AND (
           (current_candidate.email IS NOT NULL AND existing.email = current_candidate.email)
           OR (current_candidate.phone IS NOT NULL AND existing.phone = current_candidate.phone)
           OR (
             current_candidate.full_name = existing.full_name
           )
         )
        WHERE current_candidate.id = :candidate_id
        ORDER BY existing.updated_at DESC, existing.id DESC;
        """
    )
    with engine.connect() as connection:
        rows = connection.execute(query, {"candidate_id": candidate_id}).mappings().all()
    matches: list[CandidateDuplicateMatchRecord] = []
    for row in rows:
        reasons: list[str] = []
        score = 40
        if row["email"] and row["current_email"] and row["email"] == row["current_email"]:
            reasons.append("email_match")
            score += 35
        if row["phone"] and row["current_phone"] and row["phone"] == row["current_phone"]:
            reasons.append("phone_match")
            score += 35
        if row["matched_candidate_name"] == row["current_name"]:
            reasons.append("name_match")
            score += 15
        matches.append(
            CandidateDuplicateMatchRecord(
                matched_candidate_id=row["matched_candidate_id"],
                matched_candidate_name=row["matched_candidate_name"],
                email=row["email"],
                phone=row["phone"],
                current_company=row["current_company"],
                current_designation=row["current_designation"],
                duplicate_state=row["duplicate_state"],
                match_score=min(score, 100),
                match_reasons=reasons,
            )
        )
    return matches


def update_candidate_duplicate_state(engine: Engine, candidate_id: int, duplicate_state: str) -> None:
    query = text(
        """
        UPDATE dbo.candidates
        SET duplicate_check_status = :duplicate_state,
            intake_stage = CASE
              WHEN :duplicate_state = N'in-review' THEN N'duplicate-review'
              WHEN :duplicate_state IN (N'cleared', N'merged') THEN N'ready-to-save'
              ELSE intake_stage
            END,
            updated_at = SYSUTCDATETIME()
        WHERE id = :candidate_id;
        """
    )
    with engine.begin() as connection:
        connection.execute(query, {"candidate_id": candidate_id, "duplicate_state": duplicate_state})


def create_duplicate_review_case(
    engine: Engine,
    candidate_id: int,
    matched_candidate_id: int | None,
    decision_status: str,
    decision_notes: str | None,
    requested_by_user_id: int | None,
    assigned_reviewer_user_id: int | None,
) -> DuplicateReviewCaseRecord:
    mapped_status = {
        "override-requested": "pending",
        "pending": "pending",
        "approved": "merge-into-existing",
        "discarded": "cancelled",
        "continue-as-new": "continue-as-new",
        "merge-into-existing": "merge-into-existing",
        "cancelled": "cancelled",
    }.get(decision_status, "pending")
    if matched_candidate_id is None:
        return DuplicateReviewCaseRecord(
            id=0,
            candidate_id=candidate_id,
            matched_candidate_id=None,
            decision_status=mapped_status,
            decision_notes=decision_notes,
            requested_by_user_id=requested_by_user_id,
            assigned_reviewer_user_id=assigned_reviewer_user_id,
            created_at=None,
            updated_at=None,
        )
    query = text(
        """
        INSERT INTO dbo.candidate_duplicate_checks (
          candidate_id,
          matched_candidate_id,
          match_score,
          match_level,
          match_reason_json,
          decision_status,
          decided_by_user_id,
          decision_notes
        )
        OUTPUT INSERTED.id
        VALUES (
          :candidate_id,
          :matched_candidate_id,
          50,
          N'possible',
          :match_reason_json,
          :decision_status,
          :requested_by_user_id,
          :decision_notes
        );
        """
    )
    with engine.begin() as connection:
        case_id = connection.execute(
            query,
            {
                "candidate_id": candidate_id,
                "matched_candidate_id": matched_candidate_id,
                "match_reason_json": None,
                "requested_by_user_id": requested_by_user_id,
                "decision_status": mapped_status,
                "decision_notes": decision_notes,
            },
        ).scalar_one()
    return find_duplicate_review_case_by_id(engine, int(case_id))


def find_duplicate_review_case_by_id(engine: Engine, case_id: int) -> DuplicateReviewCaseRecord:
    query = text(
        """
        SELECT TOP 1
          id,
          candidate_id,
          matched_candidate_id,
          decision_status,
          decision_notes,
          decided_by_user_id AS requested_by_user_id,
          CAST(NULL AS BIGINT) AS assigned_reviewer_user_id,
          created_at,
          updated_at
        FROM dbo.candidate_duplicate_checks
        WHERE id = :case_id;
        """
    )
    with engine.connect() as connection:
        row = connection.execute(query, {"case_id": case_id}).mappings().first()
    if row is None:
        raise RuntimeError("Duplicate review case could not be reloaded")
    return DuplicateReviewCaseRecord(**row)


def finalize_candidate_into_requisition(engine: Engine, candidate_id: int, payload: CandidateFinalizePayload) -> CandidateFinalizeRecord:
    """Run as discrete statements inside one transaction: with this ODBC
    driver, a single batch that mixes DML with a trailing SELECT returns no
    rows, so the historical table-variable batch silently produced 500s."""
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                UPDATE dbo.candidates
                SET
                  profile_status = N'active',
                  intake_stage = N'finalized',
                  finalized_at = SYSUTCDATETIME(),
                  duplicate_check_status = CASE
                    WHEN duplicate_check_status = N'not-started' THEN N'cleared'
                    ELSE duplicate_check_status
                  END,
                  updated_at = SYSUTCDATETIME()
                WHERE id = :candidate_id;
                """
            ),
            {"candidate_id": candidate_id},
        )
        application_id = connection.execute(
            text(
                """
                INSERT INTO dbo.candidate_applications (
                  candidate_id,
                  requisition_id,
                  owner_user_id,
                  current_stage,
                  screening_status,
                  application_status,
                  applied_at,
                  stage_updated_at
                )
                OUTPUT INSERTED.id
                SELECT
                  :candidate_id,
                  :requisition_id,
                  :owner_user_id,
                  :initial_stage,
                  N'pending',
                  N'active',
                  SYSUTCDATETIME(),
                  SYSUTCDATETIME()
                FROM dbo.requisitions AS r
                WHERE r.id = :requisition_id;
                """
            ),
            {
                "candidate_id": candidate_id,
                "requisition_id": payload.requisition_id,
                "owner_user_id": payload.owner_user_id,
                "initial_stage": payload.initial_stage,
            },
        ).scalar_one_or_none()
        if application_id is None:
            raise RuntimeError("Requisition was not found")

        connection.execute(
            text(
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
                  NULL,
                  :initial_stage,
                  N'Candidate finalized into requisition pipeline',
                  :finalized_by_user_id,
                  SYSUTCDATETIME(),
                  N'manual'
                );
                """
            ),
            {
                "application_id": application_id,
                "initial_stage": payload.initial_stage,
                "finalized_by_user_id": payload.finalized_by_user_id or payload.owner_user_id,
            },
        )
        row = connection.execute(
            text(
                """
                SELECT
                  c.id AS candidate_id,
                  ca.requisition_id,
                  ca.id AS application_id,
                  ca.current_stage,
                  ca.application_status,
                  c.finalized_at
                FROM dbo.candidates AS c
                INNER JOIN dbo.candidate_applications AS ca
                  ON ca.id = :application_id
                WHERE c.id = :candidate_id;
                """
            ),
            {"application_id": application_id, "candidate_id": candidate_id},
        ).mappings().one()
    return CandidateFinalizeRecord(
        candidate_id=row["candidate_id"],
        requisition_id=row["requisition_id"],
        application_id=row["application_id"],
        current_stage=row["current_stage"],
        application_status=row["application_status"],
        finalized_at=row["finalized_at"],
    )


def social_profiles_for_candidate(record: CandidateRecord) -> list[dict]:
    return _parse_social_profiles(record.social_profiles_json)
