from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import Engine

from app.repositories.display_ids import find_branch_by_id

from app.core.config import settings
from app.core.security import (
    generate_session_token,
    hash_password,
    hash_session_token,
    needs_rehash,
    verify_password,
)
from app.repositories.auth import (
    LoginUserRecord,
    SessionWithUserRecord,
    find_session_with_user_by_hash,
    find_user_for_login,
    insert_user_session,
    list_resolved_permissions,
    revoke_session_by_hash,
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


def _build_scopes(role_code: str, location_id: int | None) -> PermissionScopePayload:
    if role_code == "admin":
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


def login_service(
    engine: Engine,
    payload: LoginRequest,
    ip_address: str | None,
    user_agent: str | None,
) -> LoginResponse:
    user = find_user_for_login(engine, payload.email)
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    if user.status != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is not allowed to access the system")
    if getattr(user, "tenant_status", "active") != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This company account is not active")

    # Transparent migration: legacy unsalted hashes upgrade to bcrypt on next login.
    if needs_rehash(user.password_hash):
        update_user_password_hash(engine, user_id=user.id, password_hash=hash_password(payload.password))

    token = generate_session_token()
    session_hash = hash_session_token(token)
    session = insert_user_session(
        engine,
        user_id=user.id,
        session_token_hash=session_hash,
        ip_address=ip_address,
        user_agent=user_agent,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=SESSION_TTL_HOURS),
    )
    update_last_login(engine, user.id)

    return LoginResponse(
        token=token,
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


def get_auth_context_from_token(engine: Engine, raw_token: str) -> AuthContext:
    session_hash = hash_session_token(raw_token)
    session_record = find_session_with_user_by_hash(engine, session_hash)
    if not session_record:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication is required")
    _assert_session_active(session_record)
    touch_session(engine, session_record.session.id)
    return AuthContext(
        session_id=session_record.session.id,
        session_token_hash=session_hash,
        user=session_record.user,
    )


def logout_service(engine: Engine, auth_context: AuthContext) -> LogoutResponse:
    revoke_session_by_hash(engine, auth_context.session_token_hash)
    return LogoutResponse(message="Logged out successfully")


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
        scopes=_build_scopes(auth_context.user.role_code, auth_context.user.location_id),
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
    return PasswordResetResponse(message="Password reset successfully")
