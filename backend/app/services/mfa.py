"""MFA enrolment and management for the signed-in user (Phase 3.6, D-09)."""
from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import Engine

from app.core import rate_limit
from app.core.rbac import COMPANY_SCOPE_CODE
from app.core.totp import hash_recovery_code, matching_step, new_recovery_codes, new_secret, otpauth_uri
from app.repositories.audit import insert_audit_log
from app.repositories.auth import list_resolved_permissions, revoke_user_sessions
from app.repositories.mfa import (
    claim_step,
    confirm_enrollment,
    find_mfa,
    remaining_recovery_codes,
    remove_mfa,
    start_enrollment,
    use_recovery_code,
)
from app.schemas.auth import MfaCodeRequest, MfaEnrollResponse, MfaStatusResponse, MfaVerifyResponse
from app.services.auth import AuthContext


def mfa_required_for(engine: Engine, user_id: int) -> bool:
    """D-09: required for Admins — i.e. anyone holding the Admin template's
    company-wide grant. Decided by grant, not by role code."""
    return COMPANY_SCOPE_CODE in set(list_resolved_permissions(engine, user_id))


def _audit(engine: Engine, auth_context: AuthContext, action: str) -> None:
    try:
        insert_audit_log(
            engine,
            actor_user_id=auth_context.user.id,
            location_id=auth_context.user.location_id,
            entity_type="user",
            entity_id=auth_context.user.id,
            action_type=action,
            old_values=None,
            new_values=None,
        )
    except Exception:  # noqa: BLE001 — audit must not block the security action
        pass


def mfa_status_service(engine: Engine, auth_context: AuthContext) -> MfaStatusResponse:
    mfa = find_mfa(engine, auth_context.user.id)
    enabled = mfa is not None and mfa.enabled_at is not None
    return MfaStatusResponse(
        enabled=enabled,
        pending=mfa is not None and mfa.enabled_at is None,
        required=mfa_required_for(engine, auth_context.user.id),
        recovery_codes_remaining=remaining_recovery_codes(engine, auth_context.user.id) if enabled else 0,
    )


def enroll_service(engine: Engine, auth_context: AuthContext) -> MfaEnrollResponse:
    existing = find_mfa(engine, auth_context.user.id)
    if existing is not None and existing.enabled_at is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An authenticator is already set up")
    secret = new_secret()
    start_enrollment(engine, auth_context.user.id, secret)
    return MfaEnrollResponse(secret=secret, otpauth_uri=otpauth_uri(secret, auth_context.user.email))


def verify_enrollment_service(engine: Engine, auth_context: AuthContext, payload: MfaCodeRequest) -> MfaVerifyResponse:
    rate_limit.enforce("mfa:account", str(auth_context.user.id))
    mfa = find_mfa(engine, auth_context.user.id)
    if mfa is None or mfa.enabled_at is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Start set-up first")
    step = matching_step(mfa.totp_secret, payload.code or "")
    if step is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="That code doesn't match — check the app and try again")
    codes = new_recovery_codes()
    confirm_enrollment(engine, auth_context.user.id, step, [hash_recovery_code(code) for code in codes])
    _audit(engine, auth_context, "mfa_enabled")
    return MfaVerifyResponse(enabled=True, recovery_codes=codes)


def disable_service(engine: Engine, auth_context: AuthContext, payload: MfaCodeRequest) -> None:
    """Re-verify before removing; Admins keep MFA (D-09)."""
    rate_limit.enforce("mfa:account", str(auth_context.user.id))
    mfa = find_mfa(engine, auth_context.user.id)
    if mfa is None or mfa.enabled_at is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No authenticator is set up")
    if mfa_required_for(engine, auth_context.user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Admins must keep two-step verification on (it is required for Admins).")
    ok = False
    if payload.code:
        step = matching_step(mfa.totp_secret, payload.code)
        ok = step is not None and claim_step(engine, auth_context.user.id, step)
    elif payload.recovery_code:
        ok = use_recovery_code(engine, auth_context.user.id, hash_recovery_code(payload.recovery_code))
    if not ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification code")
    remove_mfa(engine, auth_context.user.id)
    revoke_user_sessions(engine, auth_context.user.id, "mfa-disabled", except_session_id=auth_context.session_id)
    _audit(engine, auth_context, "mfa_disabled")
