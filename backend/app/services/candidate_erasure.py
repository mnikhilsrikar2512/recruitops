"""Erase one candidate's personal data (Phase 5.3, decision D-5b).

What goes: name and contact details, current/expected pay, location and
social profiles, the resume and every stored document (files too), parsed
resume text, skills, duplicate-check snapshots, and free-text notes on this
company's applications, interviews and stage history.
What stays: the candidate row as "Erased candidate", and the applications
with their stages and dates, so pipeline counts and reports stay right.

A candidate that another company also works with is NOT erased here: each
company is a separate controller and must handle its own request. The
caller gets 409 and can archive the candidate for their own company.
"""
from __future__ import annotations

from sqlalchemy import Engine, text

from app.db.maintenance import history_maintenance

OTHER_COMPANY_SQL = """
    SELECT CASE WHEN
      EXISTS (SELECT 1 FROM dbo.candidate_applications ox
                JOIN dbo.requisitions orq ON orq.id = ox.requisition_id
                JOIN dbo.branches ob ON ob.id = orq.branch_id
               WHERE ox.candidate_id = c.id AND ob.tenant_id <> :tenant)
      OR EXISTS (SELECT 1 FROM dbo.users u WHERE u.id = c.created_by_user_id AND u.tenant_id <> :tenant)
      OR EXISTS (SELECT 1 FROM dbo.branches b WHERE b.id = c.branch_id AND b.tenant_id <> :tenant)
    THEN 1 ELSE 0 END
    FROM dbo.candidates c WHERE c.id = :cid
"""


class CandidateShared(Exception):
    pass


def used_by_another_company(engine: Engine, tenant_id: int, candidate_id: int) -> bool:
    with engine.connect() as connection:
        return bool(connection.execute(text(OTHER_COMPANY_SQL), {"tenant": tenant_id, "cid": candidate_id}).scalar())


def erase_candidate(engine: Engine, tenant_id: int, candidate_id: int) -> dict:
    if used_by_another_company(engine, tenant_id, candidate_id):
        raise CandidateShared()
    params = {"cid": candidate_id}
    report: dict = {}
    with engine.begin() as connection, history_maintenance(connection):
        keys = [r[0] for r in connection.execute(text(
            "SELECT storage_key FROM dbo.candidate_documents WHERE candidate_id = :cid AND storage_key IS NOT NULL"), params).all()]
        checks = "(SELECT id FROM dbo.candidate_duplicate_checks WHERE candidate_id = :cid OR matched_candidate_id = :cid)"
        statements = {
            "duplicate_review_cases": f"DELETE FROM dbo.duplicate_review_cases WHERE candidate_id = :cid OR candidate_duplicate_check_id IN {checks}",
            "candidate_duplicate_checks": "DELETE FROM dbo.candidate_duplicate_checks WHERE candidate_id = :cid OR matched_candidate_id = :cid",
            "candidate_resume_parse_logs": "DELETE FROM dbo.candidate_resume_parse_logs WHERE candidate_id = :cid",
            "candidate_skills": "DELETE FROM dbo.candidate_skills WHERE candidate_id = :cid",
            "candidate_documents": "DELETE FROM dbo.candidate_documents WHERE candidate_id = :cid",
            "candidate_archives": "DELETE FROM dbo.candidate_archives WHERE candidate_id = :cid",
        }
        for table, sql in statements.items():
            exists = connection.execute(text("SELECT OBJECT_ID(:n, N'U')"), {"n": f"dbo.{table}"}).scalar()
            if exists is not None:
                report[table] = connection.execute(text(sql), params).rowcount or 0
        apps = "(SELECT id FROM dbo.candidate_applications WHERE candidate_id = :cid)"
        report["applications_scrubbed"] = connection.execute(text(
            """
            UPDATE dbo.candidate_applications
            SET version = version + 1, stage_reason = NULL, rejection_reason = NULL, client_feedback_notes = NULL,
                client_duplicate_notes = NULL, risk_flags_json = NULL, offer_notes = NULL, updated_at = SYSUTCDATETIME()
            WHERE candidate_id = :cid;
            """), params).rowcount or 0
        connection.execute(text(f"UPDATE dbo.interview_rounds SET feedback_notes = NULL, updated_at = SYSUTCDATETIME() WHERE candidate_application_id IN {apps};"), params)
        connection.execute(text(f"UPDATE dbo.candidate_screening_checks SET notes = NULL WHERE candidate_application_id IN {apps};"), params)
        connection.execute(text(f"UPDATE dbo.candidate_stage_history SET change_reason = NULL WHERE candidate_application_id IN {apps} AND change_reason IS NOT NULL;"), params)
        connection.execute(text(
            """
            UPDATE dbo.candidates
            SET version = version + 1,
                full_name = CONCAT(N'Erased candidate ', COALESCE(candidate_code, CAST(id AS NVARCHAR(20)))),
                email = NULL, phone = NULL, current_location = NULL, current_ctc = NULL, expected_ctc = NULL,
                current_company = NULL, current_designation = NULL, preferred_location_text = NULL,
                social_profiles_json = NULL, source_detail = NULL, source_portal = NULL,
                resume_file_name = NULL, resume_file_path = NULL, resume_uploaded_at = NULL,
                resume_parsing_status = N'erased', candidate_score = NULL,
                status = N'erased', erased_at = SYSUTCDATETIME(), updated_at = SYSUTCDATETIME()
            WHERE id = :cid;
            """), params)
    from app.core.file_storage import get_storage

    storage = get_storage()
    removed = 0
    for key in keys:
        try:
            storage.delete(key)
            removed += 1
        except Exception:  # noqa: BLE001 — row is gone; an orphan file is reported
            report.setdefault("file_errors", 0)
            report["file_errors"] += 1
    report["files_deleted"] = removed
    return report
