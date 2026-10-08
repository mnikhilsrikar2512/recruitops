"""Privacy requests (Phase 5.3; decisions D-5b, D-5c; PRD §4.17, §9.7, §12).

company_export   an admin asks; the zip is built in the background; the
                 download link works for 7 days.
company_delete   one admin asks → a SECOND admin approves in the Approvals
                 inbox (or, when there is no other admin, the requester
                 re-confirms with a two-step verification code) → 7-day
                 cooling-off, cancellable → the job runner purges the
                 company. Audit rows are held 90 days.
candidate_export one candidate's data as a zip, at once.
candidate_erase  one candidate's personal data wiped, at once, after the
                 admin types the candidate's code to confirm.
Every step is audited.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import BackgroundTasks, HTTPException, status
from sqlalchemy import Engine

from app.core.file_storage import get_storage
from app.core.totp import matching_step
from app.repositories.approval import create_approval
from app.repositories.audit import insert_audit_log
from app.repositories.mfa import claim_step, find_mfa
from app.repositories.privacy import (
    create_request,
    due_company_deletes,
    expired_exports,
    find_request,
    list_requests,
    open_company_delete,
    other_privacy_admins,
    update_request,
)
from app.schemas.approval import ApprovalCreate
from app.services import scope

COOLING_OFF_DAYS = 7
EXPORT_TTL_DAYS = 7
LINK_TTL_SECONDS = 15 * 60


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _tenant(auth_context) -> int:
    tenant_id = scope.tenant_id_of(auth_context)
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Privacy requests belong to a company user")
    return int(tenant_id)


def _audit(engine: Engine, auth_context, request_id: int, action: str, values: dict | None = None) -> None:
    insert_audit_log(
        engine,
        actor_user_id=auth_context.user.id,
        location_id=auth_context.user.location_id,
        entity_type="privacy_request",
        entity_id=request_id,
        action_type=action,
        new_values=values,
    )


def _owned(engine: Engine, auth_context, request_id: int) -> dict:
    request = find_request(engine, request_id)
    if request is None or request["tenant_id"] != _tenant(auth_context):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Privacy request was not found")
    return request


def public_view(request: dict) -> dict:
    view = {k: v for k, v in request.items() if k not in ("result_storage_key",)}
    view["download_ready"] = bool(
        request.get("result_storage_key") and request.get("status") == "completed"
        and request.get("result_expires_at") and _aware(request["result_expires_at"]) > _now()
    )
    return view


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def list_service(engine: Engine, auth_context) -> list[dict]:
    return [public_view(r) for r in list_requests(engine, _tenant(auth_context))]


def detail_service(engine: Engine, auth_context, request_id: int) -> dict:
    return public_view(_owned(engine, auth_context, request_id))


# ---- exports ---------------------------------------------------------------
def _run_company_export(engine: Engine, tenant_id: int, request_id: int) -> None:
    from app.services.privacy_export import build_company_export

    try:
        key, size, summary = build_company_export(engine, tenant_id, request_id)
        update_request(engine, request_id, status="completed", completed_at=_now(), result_storage_key=key,
                       result_bytes=size, result_expires_at=_now() + timedelta(days=EXPORT_TTL_DAYS), summary=summary)
    except Exception as exc:  # noqa: BLE001 — recorded on the request
        update_request(engine, request_id, status="failed", completed_at=_now(), error=str(exc)[:2000])


def company_export_service(engine: Engine, auth_context, background: BackgroundTasks | None) -> dict:
    tenant_id = _tenant(auth_context)
    request_id = create_request(
        engine, tenant_id=tenant_id, request_type="company_export", status="processing",
        requested_by_user_id=auth_context.user.id, requested_by_name=auth_context.user.full_name, started_at=_now(),
    )
    _audit(engine, auth_context, request_id, "privacy.export_requested", {"scope": "company"})
    if background is not None:
        background.add_task(_run_company_export, engine, tenant_id, request_id)
    else:
        _run_company_export(engine, tenant_id, request_id)
    return detail_service(engine, auth_context, request_id)


def _candidate_in_company(engine: Engine, auth_context, candidate_id: int) -> dict:
    from sqlalchemy import text

    tenant_id = _tenant(auth_context)
    if not scope.candidate_in_tenant(engine, candidate_id, tenant_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate was not found")
    with engine.connect() as connection:
        row = connection.execute(text("SELECT id, candidate_code, full_name, erased_at FROM dbo.candidates WHERE id = :id"),
                                 {"id": candidate_id}).mappings().first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate was not found")
    return dict(row)


def candidate_export_service(engine: Engine, auth_context, candidate_id: int) -> dict:
    from app.services.privacy_export import build_candidate_export

    tenant_id = _tenant(auth_context)
    _candidate_in_company(engine, auth_context, candidate_id)
    request_id = create_request(
        engine, tenant_id=tenant_id, request_type="candidate_export", candidate_id=candidate_id, status="processing",
        requested_by_user_id=auth_context.user.id, requested_by_name=auth_context.user.full_name, started_at=_now(),
    )
    _audit(engine, auth_context, request_id, "privacy.candidate_exported", {"candidate_id": candidate_id})
    try:
        key, size, summary = build_candidate_export(engine, tenant_id, candidate_id, request_id)
    except Exception as exc:
        update_request(engine, request_id, status="failed", completed_at=_now(), error=str(exc)[:2000])
        raise
    update_request(engine, request_id, status="completed", completed_at=_now(), result_storage_key=key, result_bytes=size,
                   result_expires_at=_now() + timedelta(days=EXPORT_TTL_DAYS), summary=summary)
    return detail_service(engine, auth_context, request_id)


def download_service(engine: Engine, auth_context, request_id: int) -> dict:
    request = _owned(engine, auth_context, request_id)
    if not public_view(request)["download_ready"]:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="There is no download for this request (not ready, or expired)")
    name = f"recruitops-{request['request_type'].replace('_', '-')}-{request_id}.zip"
    url = get_storage().link(request["result_storage_key"], name, "application/zip", LINK_TTL_SECONDS)
    _audit(engine, auth_context, request_id, "privacy.export_downloaded")
    return {"url": url, "expires_in_seconds": LINK_TTL_SECONDS}


# ---- candidate erasure -----------------------------------------------------
def candidate_erase_service(engine: Engine, auth_context, candidate_id: int, confirm: str, reason: str | None) -> dict:
    from app.services.candidate_erasure import CandidateShared, erase_candidate

    tenant_id = _tenant(auth_context)
    candidate = _candidate_in_company(engine, auth_context, candidate_id)
    if candidate["erased_at"] is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This candidate has already been erased")
    expected = candidate["candidate_code"] or str(candidate_id)
    if (confirm or "").strip().upper() != expected.upper():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                            detail=f"Type the candidate's ID ({expected}) to confirm the erasure")
    request_id = create_request(
        engine, tenant_id=tenant_id, request_type="candidate_erase", candidate_id=candidate_id, status="processing",
        reason=reason, requested_by_user_id=auth_context.user.id, requested_by_name=auth_context.user.full_name, started_at=_now(),
    )
    try:
        report = erase_candidate(engine, tenant_id, candidate_id)
    except CandidateShared:
        update_request(engine, request_id, status="rejected", completed_at=_now(),
                       error="Another company also works with this candidate")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Another company also works with this candidate, so it can't be erased from here. "
                   "Archive the candidate to remove them from your company; the other company must handle its own request.",
        ) from None
    update_request(engine, request_id, status="completed", completed_at=_now(), summary=report)
    _audit(engine, auth_context, request_id, "privacy.candidate_erased", {"candidate_id": candidate_id, **report})
    return detail_service(engine, auth_context, request_id)


# ---- company delete ----------------------------------------------------------
def company_delete_service(engine: Engine, auth_context, reason: str) -> dict:
    tenant_id = _tenant(auth_context)
    if open_company_delete(engine, tenant_id):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A delete request for this company is already open")
    request_id = create_request(
        engine, tenant_id=tenant_id, request_type="company_delete", status="pending_approval", reason=reason,
        requested_by_user_id=auth_context.user.id, requested_by_name=auth_context.user.full_name,
    )
    others = other_privacy_admins(engine, tenant_id, auth_context.user.id)
    office_id = auth_context.user.location_id or _first_office(engine, tenant_id)
    if office_id:
        approval = create_approval(engine, ApprovalCreate(
            location_id=office_id, approval_type="privacy-delete",
            related_entity_type="privacy_request", related_entity_id=request_id,
            title="Delete ALL company data", priority="high", requester_user_id=auth_context.user.id,
            description=(f"{auth_context.user.full_name} asked to permanently delete every record of the company. "
                         f"Reason: {reason}. After approval there are {COOLING_OFF_DAYS} days to cancel."),
        ))
        update_request(engine, request_id, approval_id=approval.id)
    _audit(engine, auth_context, request_id, "privacy.delete_requested", {"reason": reason, "other_admins": len(others)})
    view = detail_service(engine, auth_context, request_id)
    view["needs_self_confirmation"] = not others
    return view


def _first_office(engine: Engine, tenant_id: int) -> int | None:
    from sqlalchemy import text

    with engine.connect() as connection:
        return connection.execute(text("SELECT MIN(id) FROM dbo.branches WHERE tenant_id = :t"), {"t": tenant_id}).scalar()


def _schedule(engine: Engine, request_id: int, approver_id: int, method: str) -> None:
    update_request(engine, request_id, status="scheduled", approved_by_user_id=approver_id, approved_at=_now(),
                   approval_method=method, execute_after=_now() + timedelta(days=COOLING_OFF_DAYS))


def on_delete_approval_decided(engine: Engine, approval, decision: str, decider_id: int) -> None:
    """Hook from the Approvals inbox (app/services/approval.py). Checks are
    made BEFORE the approval row changes (see assert_can_decide)."""
    request = find_request(engine, int(approval.related_entity_id))
    if request is None or request["status"] != "pending_approval":
        return
    if decision == "approved":
        _schedule(engine, request["id"], decider_id, "second_admin")
    else:
        update_request(engine, request["id"], status="rejected", completed_at=_now())


def assert_can_decide(engine: Engine, approval, decider_id: int | None) -> None:
    request = find_request(engine, int(approval.related_entity_id))
    if request is None:
        return
    if decider_id is None or decider_id == request["requested_by_user_id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="A different admin must approve a company delete request")
    from app.repositories.auth import list_resolved_permissions

    if "privacy_request.write" not in set(list_resolved_permissions(engine, decider_id)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only a company admin can approve a company delete request")


def self_confirm_service(engine: Engine, auth_context, request_id: int, code: str) -> dict:
    from app.repositories.approval import decide_approval
    from app.schemas.approval import ApprovalDecision

    request = _owned(engine, auth_context, request_id)
    if request["request_type"] != "company_delete" or request["status"] != "pending_approval":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This request is not waiting for confirmation")
    if request["requested_by_user_id"] != auth_context.user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the admin who asked can confirm it")
    if other_privacy_admins(engine, request["tenant_id"], auth_context.user.id):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail="Another admin must approve this in the Approvals inbox")
    mfa = find_mfa(engine, auth_context.user.id)
    if mfa is None or mfa.enabled_at is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Set up two-step verification first, then confirm")
    step = matching_step(mfa.totp_secret, code or "")
    if step is None or not claim_step(engine, auth_context.user.id, step):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="That code doesn't match — check the app and try again")
    _schedule(engine, request_id, auth_context.user.id, "sole_admin_mfa")
    if request.get("approval_id"):
        try:
            decide_approval(engine, int(request["approval_id"]), ApprovalDecision(
                decision="approved", decision_user_id=auth_context.user.id,
                decision_notes="Confirmed by the only admin with two-step verification"))
        except ValueError:
            pass
    _audit(engine, auth_context, request_id, "privacy.delete_confirmed", {"method": "sole_admin_mfa"})
    return detail_service(engine, auth_context, request_id)


def cancel_service(engine: Engine, auth_context, request_id: int) -> dict:
    from app.repositories.approval import decide_approval
    from app.schemas.approval import ApprovalDecision

    request = _owned(engine, auth_context, request_id)
    if request["request_type"] != "company_delete" or request["status"] not in ("pending_approval", "scheduled"):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only a delete request that hasn't run yet can be cancelled")
    update_request(engine, request_id, status="cancelled", cancelled_by_user_id=auth_context.user.id, cancelled_at=_now())
    if request["status"] == "pending_approval" and request.get("approval_id"):
        try:
            decide_approval(engine, int(request["approval_id"]), ApprovalDecision(
                decision="rejected", decision_user_id=auth_context.user.id, decision_notes="Request cancelled"))
        except ValueError:
            pass
    _audit(engine, auth_context, request_id, "privacy.delete_cancelled")
    return detail_service(engine, auth_context, request_id)


# ---- job runner (scripts/run_privacy_jobs.py, cron) ----------------------------
def run_due_jobs(engine: Engine) -> dict:
    from app.services.tenant_purge import purge_company, release_expired_holds

    result = {"purged": [], "failed": [], "holds_released": 0, "exports_expired": 0}
    for request in due_company_deletes(engine):
        update_request(engine, request["id"], status="processing", started_at=_now())
        try:
            report = purge_company(engine, request["tenant_id"], request["id"])
            update_request(engine, request["id"], status="completed", completed_at=_now(), summary=report)
            result["purged"].append(request["tenant_id"])
        except Exception as exc:  # noqa: BLE001 — recorded; ops looks at failed requests
            update_request(engine, request["id"], status="failed", completed_at=_now(), error=str(exc)[:2000])
            result["failed"].append(request["id"])
    result["holds_released"] = release_expired_holds(engine)
    storage = get_storage()
    for request in expired_exports(engine):
        try:
            storage.delete(request["result_storage_key"])
        except Exception:  # noqa: BLE001
            pass
        update_request(engine, request["id"], result_storage_key=None)
        result["exports_expired"] += 1
    return result
