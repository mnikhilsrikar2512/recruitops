from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import Engine

from app.core.rbac import COMPANY_SCOPE_CODE
from app.repositories.display_ids import find_branch_by_id

from app.core.config import settings
from app.core.security import (
    generate_session_token,
    hash_password,
    hash_session_token,
    needs_rehash,
    verify_password,
)
from app.core.tokens import (
    InvalidToken,
    decode_access_token,
    hash_refresh_token,
    issue_access_token,
    looks_like_jwt,
    new_refresh_token,
)
from app.repositories.auth import (
    LoginUserRecord,
    SessionWithUserRecord,
    find_refresh_token,
    find_session_with_user_by_hash,
    find_session_with_user_by_id,
    find_user_for_login,
    insert_refresh_token,
    insert_user_session,
    list_active_sessions,
    list_resolved_permissions,
    mark_refresh_token_used,
    record_failed_login,
    reset_failed_logins,
    revoke_session,
    revoke_session_by_hash,
    revoke_user_sessions,
    touch_session,
    update_last_login,
)
from app.repositories.audit import insert_audit_log
from app.repositories.users import (
    create_password_reset_token,
    find_user_by_email,
    find_valid_password_reset_token,
    mark_password_reset_token_used,
    update_own_profile_fields,
    update_user_password_hash,
    update_user_password_state,
)
from app.schemas.auth import (
    CurrentSessionResponse,
    LoginRequest,
    LoginResponse,
    LogoutResponse,
    PasswordChangeRequest,
    PasswordChangeResponse,
    PasswordForgotRequest,
    PasswordForgotResponse,
    PasswordResetRequest,
    PasswordResetResponse,
    PasswordSetupRequest,
    PasswordSetupResponse,
    ProfileUpdateRequest,
)
from app.schemas.permission import PermissionScopePayload, ResolvedPermissionsResponse

SESSION_TTL_HOURS = settings.session_ttl_hours


@dataclass
class AuthContext:
    session_id: int
    session_token_hash: str
    user: LoginUserRecord
    # Set by the API from the scope.company grant; None in hand-built contexts.
    company_wide: bool | None = None


def _build_allowed_pages(permission_codes: list[str]) -> list[str]:
    page_map = [
        ("dashboard.read_my_work", "Role Dashboard"),
        ("requisition.read", "Requisition Detail"),
        ("pipeline.read.summary", "Pipeline Board"),
        ("client.read", "Client Directory"),
        ("user.read", "User Directory"),
        ("location.read", "Location Management"),
    ]
    return [page for permission, page in page_map if permission in permission_codes]


def _build_scopes(company_wide: bool, location_id: int | None) -> PermissionScopePayload:
    if company_wide:
        # "global" here means every office of the user's OWN company.
        return PermissionScopePayload(
            clients="global",
            requisitions="global",
            candidates="global",
            locations="global",
            location_ids=None,
        )

    return PermissionScopePayload(
        clients="location",
        requisitions="location",
        candidates="linked-or-permitted",
        locations="assigned",
        location_ids=[location_id] if location_id else [],
    )


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _assert_session_active(session_record: SessionWithUserRecord) -> None:
    if session_record.session.revoked_at or _as_utc(session_record.session.expires_at) < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session is no longer active")
    if session_record.user.status != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is not allowed to access the system")
    if getattr(session_record.user, "tenant_status", "active") != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This company account is not active")


def _branch_offers_enabled(engine: Engine, location_id: int | None) -> bool | None:
    """Resolve the branch offer-tracking flag for the session's primary location.

    None (unknown branch / legacy column) means "no information" — the
    frontend treats that as enabled so the default flow is unchanged.
    """
    if location_id is None:
        return None
    branch = find_branch_by_id(engine, location_id)
    return branch.offers_enabled if branch else None


def _current_session_payload(user: LoginUserRecord, engine: Engine | None = None) -> CurrentSessionResponse:
    return CurrentSessionResponse(
        user={
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "status": user.status,
            "business_title": getattr(user, "business_title", None),
            "phone": getattr(user, "phone", None),
            "employee_code": getattr(user, "employee_code", None),
        },
        primary_role={
            "id": user.role_id,
            "code": user.role_code,
            "name": user.role_name,
        },
        primary_location={
            "id": user.location_id,
            "location_code": user.location_code,
            "location_name": user.location_name,
            "offers_enabled": _branch_offers_enabled(engine, user.location_id) if engine is not None else None,
        },
    )


def _refresh_expiry(session_expires_at: datetime) -> datetime:
    """Idle expiry of a refresh token, never past the sign-in's absolute cap."""
    idle = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_ttl_days)
    return min(idle, _as_utc(session_expires_at))


def _start_session(
    engine: Engine, user: LoginUserRecord, ip_address: str | None, user_agent: str | None
) -> tuple[object, str, str, datetime]:
    """New sign-in = new refresh-token family. Returns (session, access, refresh, access_expiry)."""
    session = insert_user_session(
        engine,
        user_id=user.id,
        # NOT NULL legacy column; never accepted as a credential for JWT sessions.
        session_token_hash=hash_session_token(generate_session_token()),
        ip_address=ip_address,
        user_agent=(user_agent or "")[:1000] or None,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.session_absolute_ttl_days),
        auth_kind="jwt",
    )
    refresh_raw, refresh_hash = new_refresh_token()
    insert_refresh_token(engine, session.id, refresh_hash, _refresh_expiry(session.expires_at)
                         if isinstance(session.expires_at, datetime)
                         else datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_ttl_days))
    access, access_expires_at = issue_access_token(
        user_id=user.id, tenant_id=getattr(user, "tenant_id", None), session_id=session.id
    )
    return session, access, refresh_raw, access_expires_at


def login_service(
    engine: Engine,
    payload: LoginRequest,
    ip_address: str | None,
    user_agent: str | None,
) -> tuple[LoginResponse, str]:
    """Returns the response body and the raw refresh token (set as an
    HttpOnly cookie by the endpoint, never put in the body)."""
    user = find_user_for_login(engine, payload.email)
    locked_until = getattr(user, "locked_until", None) if user else None
    if locked_until is not None and _as_utc(locked_until) > datetime.now(timezone.utc):
        # Lockout/backoff (Phase 3.5): no password check while locked.
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed sign-in attempts. Try again later or reset your password.",
        )
    if not user or not verify_password(payload.password, user.password_hash):
        if user:
            record_failed_login(engine, user.id, settings.login_lockout_threshold, settings.login_lockout_minutes)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    reset_failed_logins(engine, user.id)  # a correct password clears the count
    if user.status != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is not allowed to access the system")
    if getattr(user, "tenant_status", "active") != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This company account is not active")

    # Transparent migration: legacy unsalted hashes upgrade to bcrypt on next login.
    if needs_rehash(user.password_hash):
        update_user_password_hash(engine, user_id=user.id, password_hash=hash_password(payload.password))

    session, token, refresh_raw, access_expires_at = _start_session(engine, user, ip_address, user_agent)
    update_last_login(engine, user.id)

    body = LoginResponse(
        token=token,
        access_expires_at=access_expires_at,
        user={
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "status": user.status,
            "business_title": getattr(user, "business_title", None),
            "phone": getattr(user, "phone", None),
            "employee_code": getattr(user, "employee_code", None),
        },
        primary_role={
            "id": user.role_id,
            "code": user.role_code,
            "name": user.role_name,
        },
        primary_location={
            "id": user.location_id,
            "location_code": user.location_code,
            "location_name": user.location_name,
            "offers_enabled": _branch_offers_enabled(engine, user.location_id),
        },
        session={
            "id": session.id,
            "expires_at": session.expires_at,
            "force_password_change_on_first_login": user.force_password_change_on_first_login,
        },
    )
    return body, refresh_raw


def _unauthorized(detail: str = "Authentication is required") -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


def get_auth_context_from_token(engine: Engine, raw_token: str) -> AuthContext:
    """Bearer JWT → active session → user. Pre-JWT opaque tokens are refused
    (one-release cutover, D-08)."""
    if not looks_like_jwt(raw_token):
        raise _unauthorized()
    try:
        claims = decode_access_token(raw_token)
    except InvalidToken:
        raise _unauthorized("Session is no longer active") from None
    session_record = find_session_with_user_by_id(engine, int(claims["sid"]))
    if not session_record or str(session_record.user.id) != str(claims["sub"]):
        raise _unauthorized()
    _assert_session_active(session_record)
    touch_session(engine, session_record.session.id)
    return AuthContext(
        session_id=session_record.session.id,
        session_token_hash="",
        user=session_record.user,
    )


def logout_service(engine: Engine, auth_context: AuthContext) -> LogoutResponse:
    # The whole sign-in ends: its access tokens stop at the next request and
    # its refresh tokens can no longer be used.
    revoke_session(engine, auth_context.session_id, "logout")
    return LogoutResponse(message="Logged out successfully")


def refresh_service(engine: Engine, refresh_raw: str | None) -> tuple[dict, str]:
    """Rotate: a refresh token is used exactly once. Re-using a used token is
    treated as theft and revokes the whole sign-in (family). Expired or
    revoked → 401, full re-login."""
    if not refresh_raw:
        raise _unauthorized()
    token = find_refresh_token(engine, hash_refresh_token(refresh_raw))
    if token is None:
        raise _unauthorized()
    if token.used_at is not None or not mark_refresh_token_used(engine, token.id):
        revoke_session(engine, token.session_id, "refresh-reuse")
        raise _unauthorized("Session is no longer active")
    if _as_utc(token.expires_at) < datetime.now(timezone.utc):
        raise _unauthorized("Session is no longer active")
    record = find_session_with_user_by_id(engine, token.session_id)
    if record is None:
        raise _unauthorized()
    _assert_session_active(record)
    refresh_raw_next, refresh_hash = new_refresh_token()
    insert_refresh_token(engine, record.session.id, refresh_hash, _refresh_expiry(record.session.expires_at))
    access, access_expires_at = issue_access_token(
        user_id=record.user.id, tenant_id=getattr(record.user, "tenant_id", None), session_id=record.session.id
    )
    return {"token": access, "access_expires_at": access_expires_at}, refresh_raw_next


def list_sessions_service(engine: Engine, auth_context: AuthContext) -> dict:
    items = list_active_sessions(engine, auth_context.user.id)
    for item in items:
        item["current"] = item["id"] == auth_context.session_id
    return {"items": items}


def revoke_own_session_service(engine: Engine, auth_context: AuthContext, session_id: int) -> None:
    owned = {item["id"] for item in list_active_sessions(engine, auth_context.user.id)}
    if session_id not in owned:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session was not found")
    revoke_session(engine, session_id, "user-revoked")


def revoke_other_sessions_service(engine: Engine, auth_context: AuthContext) -> int:
    return revoke_user_sessions(engine, auth_context.user.id, "user-revoked-others", except_session_id=auth_context.session_id)


def get_current_session_service(engine: Engine, auth_context: AuthContext) -> CurrentSessionResponse:
    return _current_session_payload(auth_context.user, engine)


def update_own_profile_service(
    engine: Engine,
    auth_context: AuthContext,
    payload: ProfileUpdateRequest,
) -> CurrentSessionResponse:
    has_full_name = "full_name" in payload.model_fields_set
    has_phone = "phone" in payload.model_fields_set
    old_values = {
        "full_name": auth_context.user.full_name,
        "phone": getattr(auth_context.user, "phone", None),
    }
    update_own_profile_fields(
        engine,
        auth_context.user.id,
        full_name=payload.full_name,
        phone=payload.phone,
        has_full_name=has_full_name,
        has_phone=has_phone,
    )
    insert_audit_log(
        engine,
        actor_user_id=auth_context.user.id,
        location_id=auth_context.user.location_id,
        entity_type="user",
        entity_id=auth_context.user.id,
        action_type="profile_updated",
        old_values=old_values,
        new_values={
            "full_name": payload.full_name if has_full_name else old_values["full_name"],
            "phone": payload.phone if has_phone else old_values["phone"],
        },
    )
    refreshed = find_user_for_login(engine, auth_context.user.email)
    if not refreshed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User was not found")
    return _current_session_payload(refreshed, engine)


def get_resolved_permissions_service(engine: Engine, auth_context: AuthContext) -> ResolvedPermissionsResponse:
    permissions = list_resolved_permissions(engine, auth_context.user.id)
    return ResolvedPermissionsResponse(
        role_code=auth_context.user.role_code,
        permissions=permissions,
        scopes=_build_scopes(COMPANY_SCOPE_CODE in permissions, auth_context.user.location_id),
        allowed_pages=_build_allowed_pages(permissions),
    )


def change_password_service(
    engine: Engine,
    auth_context: AuthContext,
    payload: PasswordChangeRequest,
) -> PasswordChangeResponse:
    user = find_user_for_login(engine, auth_context.user.email)
    if not user or not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    update_user_password_state(
        engine,
        user_id=auth_context.user.id,
        password_hash=hash_password(payload.new_password),
        password_setup_status="setup-complete",
        force_password_change_on_first_login=False,
    )
    # Every other sign-in of this user ends; this one continues.
    revoke_user_sessions(engine, auth_context.user.id, "password-change", except_session_id=auth_context.session_id)
    return PasswordChangeResponse(message="Password changed successfully")


def setup_password_service(
    engine: Engine,
    payload: PasswordSetupRequest,
) -> PasswordSetupResponse:
    from app.core.security import sha256_hex

    token_hash = sha256_hex(payload.token)
    token_record = find_valid_password_reset_token(engine, token_hash, "admin-reset")
    if not token_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired setup token",
        )
    update_user_password_state(
        engine,
        user_id=token_record["user_id"],
        password_hash=hash_password(payload.new_password),
        password_setup_status="setup-complete",
        force_password_change_on_first_login=False,
    )
    mark_password_reset_token_used(engine, token_record["id"])
    return PasswordSetupResponse(message="Password set successfully")


def forgot_password_service(
    engine: Engine,
    payload: PasswordForgotRequest,
) -> PasswordForgotResponse:
    user = find_user_by_email(engine, payload.email)
    if not user:
        return PasswordForgotResponse(
            message="If an account with that email exists, a reset link has been sent"
        )
    if user.status != "active":
        return PasswordForgotResponse(
            message="If an account with that email exists, a reset link has been sent"
        )
    setup_token = generate_session_token()
    create_password_reset_token(
        engine,
        user_id=user.id,
        token_hash=hash_session_token(setup_token),
        purpose="self-reset",
        issued_by_user_id=user.id,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=settings.token_expiry_hours),
    )
    return PasswordForgotResponse(
        message="If an account with that email exists, a reset link has been sent"
    )


def reset_password_service(
    engine: Engine,
    payload: PasswordResetRequest,
) -> PasswordResetResponse:
    from app.core.security import sha256_hex

    token_hash = sha256_hex(payload.token)
    token_record = find_valid_password_reset_token(engine, token_hash, "self-reset")
    if not token_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )
    update_user_password_state(
        engine,
        user_id=token_record["user_id"],
        password_hash=hash_password(payload.new_password),
        password_setup_status="setup-complete",
        force_password_change_on_first_login=False,
    )
    mark_password_reset_token_used(engine, token_record["id"])
    revoke_user_sessions(engine, token_record["user_id"], "password-reset")
    return PasswordResetResponse(message="Password reset successfully")
