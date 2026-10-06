from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import Engine
from app.core.config import settings
from app.core.security import hash_password, hash_session_token, random_secret

from app.repositories.audit import insert_audit_log
from app.repositories.users import (
    count_active_admins,
    count_user_active_assignments,
    count_user_active_candidate_ownership,
    count_user_active_pipeline_ownership,
    count_user_active_requisitions,
    create_password_reset_token,
    create_user,
    find_user_by_email,
    find_user_by_employee_code,
    find_user_by_id,
    list_users,
    location_exists,
    role_exists,
    transfer_active_user_work_and_deactivate,
    transfer_active_user_work_and_move,
    update_user,
    update_user_password_state,
)
from sqlalchemy import text
from app.schemas.notification import NotificationCreate
from app.schemas.pagination import PaginationMeta
from app.schemas.user import (
    UserCreate,
    UserDeactivateRequest,
    UserDeactivationResponse,
    UserListFilters,
    UserListResponse,
    UserMoveRequest,
    UserMoveResponse,
    UserResetCredentials,
    UserResetCredentialsResponse,
    UserResponse,
    UserUpdate,
)
from app.services.auth import AuthContext
from app.services.notifications import create_notification_service


def _assert_user_references(
    engine: Engine,
    primary_location_id: int | None = None,
    primary_role_id: int | None = None,
    reporting_manager_user_id: int | None = None,
    user_id_to_exclude: int | None = None,
) -> None:
    if primary_location_id and not location_exists(engine, primary_location_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Primary location was not found")

    if primary_role_id and not role_exists(engine, primary_role_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Primary role was not found")

    if reporting_manager_user_id is not None:
        if reporting_manager_user_id == user_id_to_exclude:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user cannot report to themselves",
            )
        manager = find_user_by_id(engine, reporting_manager_user_id)
        if not manager:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reporting manager was not found",
            )


def _assert_transfer_target(
    engine: Engine,
    user_id: int,
    transfer_to_user_id: int | None,
    actor_location_id: int | None,
) -> None:
    if transfer_to_user_id is None:
        return
    if transfer_to_user_id == user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Transfer user cannot be the same user")
    transfer_user = find_user_by_id(engine, transfer_to_user_id)
    if not transfer_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transfer user was not found")
    if transfer_user.status != "active":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Transfer user must be active")
    if actor_location_id is not None and transfer_user.primary_location_id != actor_location_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Transfer user must belong to the same location")


def list_users_service(engine: Engine, filters: UserListFilters) -> UserListResponse:
    items, total = list_users(engine, filters)
    return UserListResponse(
        items=[UserResponse.model_validate(item) for item in items],
        meta=PaginationMeta(page=filters.page, page_size=filters.page_size, total=total),
    )


def get_user_detail_service(engine: Engine, user_id: int) -> UserResponse:
    existing = find_user_by_id(engine, user_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User was not found")
    return UserResponse.model_validate(existing)


def create_user_service(engine: Engine, payload: UserCreate) -> UserResponse:
    if find_user_by_email(engine, str(payload.email)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists")

    if find_user_by_employee_code(engine, payload.employee_code):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Employee code already exists")

    _assert_user_references(
        engine,
        primary_location_id=payload.primary_location_id,
        primary_role_id=payload.primary_role_id,
        reporting_manager_user_id=payload.reporting_manager_user_id,
    )

    created = create_user(engine, payload, hash_password(random_secret(24)))
    return UserResponse.model_validate(created)


def update_user_service(engine: Engine, user_id: int, payload: UserUpdate) -> UserResponse:
    existing = find_user_by_id(engine, user_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User was not found")

    _assert_user_references(
        engine,
        primary_location_id=payload.primary_location_id,
        primary_role_id=payload.primary_role_id,
        reporting_manager_user_id=payload.reporting_manager_user_id,
        user_id_to_exclude=user_id,
    )    # Never allow the last active admin to lose the admin role — this account
    # is the only path to role/user configuration, so demoting it would lock
    # the workspace out of its own settings.
    next_role_id = payload.primary_role_id or existing.primary_role_id
    if (
        existing.primary_role_code == "admin"
        and next_role_id != existing.primary_role_id
        and count_active_admins(engine, user_id) <= 1
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot change the role of the last active admin",
        )

    # Status changes must not bypass the deactivate flow's lockout guard —
    # PATCH with {"status": "inactive"} would otherwise suspend or
    # deactivate the last active admin without any of the work-transfer
    # review the dedicated endpoint enforces. Only non-active targets are
    # blocked, so a legacy suspended admin can still be restored to active.
    if (
        payload.status is not None
        and payload.status != "active"
        and existing.primary_role_code == "admin"
        and count_active_admins(engine, user_id) <= 1
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot deactivate the last active admin via status update; use the deactivate flow",
        )

    updated = update_user(engine, user_id, payload, existing)
    return UserResponse.model_validate(updated)


def reset_user_credentials_service(
    engine: Engine,
    user_id: int,
    payload: UserResetCredentials,
) -> UserResetCredentialsResponse:
    existing = find_user_by_id(engine, user_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User was not found")

    if payload.mode == "temporary-password":
        temporary_password = random_secret(8)
        update_user_password_state(
            engine,
            user_id=user_id,
            password_hash=hash_password(temporary_password),
            password_setup_status="reset-required",
            force_password_change_on_first_login=True,
        )
        return UserResetCredentialsResponse(
            user_id=user_id,
            mode=payload.mode,
            temporary_password=temporary_password,
            password_setup_status="reset-required",
        )

    # Clean up any stale unused tokens for this user before creating a new one
    _mark_stale_tokens_used(engine, user_id, "admin-reset")

    setup_token = random_secret(24)
    try:
        create_password_reset_token(
            engine,
            user_id=user_id,
            token_hash=hash_session_token(setup_token),
            purpose="admin-reset",
            issued_by_user_id=payload.issued_by_user_id,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=settings.token_expiry_hours),
        )
    except Exception:
        # Unique constraint violation — mark existing tokens used and retry once
        _mark_stale_tokens_used(engine, user_id, "admin-reset")
        create_password_reset_token(
            engine,
            user_id=user_id,
            token_hash=hash_session_token(setup_token),
            purpose="admin-reset",
            issued_by_user_id=payload.issued_by_user_id,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=settings.token_expiry_hours),
        )

    update_user_password_state(
        engine,
        user_id=user_id,
        password_hash=hash_password(random_secret(24)),
        password_setup_status="reset-required",
        force_password_change_on_first_login=True,
    )
    return UserResetCredentialsResponse(
        user_id=user_id,
        mode=payload.mode,
        setup_token=setup_token,
        expires_in_hours=24,
        password_setup_status="reset-required",
    )


def _mark_stale_tokens_used(engine: Engine, user_id: int, purpose: str) -> None:
    """Mark all unused tokens for the given user and purpose as used."""
    query = text(
        """
        UPDATE dbo.password_reset_tokens
        SET used_at = SYSUTCDATETIME()
        WHERE user_id = :user_id
        AND purpose = :purpose
        AND used_at IS NULL
        """
    )
    with engine.begin() as connection:
        connection.execute(query, {"user_id": user_id, "purpose": purpose})


def deactivate_user_service(
    engine: Engine,
    user_id: int,
    payload: UserDeactivateRequest,
    auth_context: AuthContext | None = None,
) -> UserDeactivationResponse:
    existing = find_user_by_id(engine, user_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User was not found")
    if existing.status == "inactive":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User is already inactive")
    # Same lockout rule as the role-change guard: the workspace must always
    # keep at least one active admin account.
    if existing.primary_role_code == "admin" and count_active_admins(engine, user_id) <= 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot deactivate the last active admin",
        )

    actor_location_id = existing.primary_location_id
    _assert_transfer_target(engine, user_id, payload.transfer_to_user_id, actor_location_id)

    active_requisition_count = count_user_active_requisitions(engine, user_id)
    active_assignment_count = count_user_active_assignments(engine, user_id)
    active_candidate_owner_count = count_user_active_candidate_ownership(engine, user_id)
    active_pipeline_owner_count = count_user_active_pipeline_ownership(engine, user_id)
    review_required = any(
        count > 0
        for count in (
            active_requisition_count,
            active_assignment_count,
            active_candidate_owner_count,
            active_pipeline_owner_count,
        )
    )

    if review_required and not payload.review_confirmed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User deactivation requires active-work review confirmation",
        )
    if review_required and payload.transfer_to_user_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Transfer user is required when active work exists",
        )

    updated = transfer_active_user_work_and_deactivate(
        engine,
        user_id=user_id,
        transfer_to_user_id=payload.transfer_to_user_id,
    )
    try:
        create_notification_service(
            engine,
            NotificationCreate(
                location_id=existing.primary_location_id,
                user_id=user_id,
                event_type="user_deactivated",
                source_type="user",
                source_id=user_id,
                title="Your account was deactivated",
                message=(
                    "Your account has been deactivated and your active work was transferred "
                    "to another user. Contact your administrator if you believe this is a mistake."
                ),
                priority="high",
                action_url=None,
            ),
        )
    except Exception:
        pass
    actor_user_id = payload.changed_by_user_id or (auth_context.user.id if auth_context else None)
    if actor_user_id is not None:
        insert_audit_log(
            engine,
            actor_user_id=actor_user_id,
            location_id=existing.primary_location_id,
            entity_type="user",
            entity_id=user_id,
            action_type="deactivated_with_transfer",
            old_values={"status": existing.status},
            new_values={
                "status": updated.status,
                "transfer_to_user_id": payload.transfer_to_user_id,
                "reason": payload.reason,
                "review_confirmed": payload.review_confirmed,
                "active_requisition_count": active_requisition_count,
                "active_assignment_count": active_assignment_count,
                "active_candidate_owner_count": active_candidate_owner_count,
                "active_pipeline_owner_count": active_pipeline_owner_count,
            },
        )

    return UserDeactivationResponse(
        user_id=user_id,
        previous_status=existing.status,
        new_status=updated.status,
        transfer_to_user_id=payload.transfer_to_user_id,
        review_required=review_required,
        active_requisition_count=active_requisition_count,
        active_assignment_count=active_assignment_count,
        active_candidate_owner_count=active_candidate_owner_count,
        active_pipeline_owner_count=active_pipeline_owner_count,
        reason=payload.reason,
    )


def move_user_service(
    engine: Engine,
    user_id: int,
    payload: UserMoveRequest,
    auth_context: AuthContext | None = None,
) -> UserMoveResponse:
    existing = find_user_by_id(engine, user_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User was not found")

    next_primary_location_id = payload.new_primary_location_id or existing.primary_location_id
    next_primary_role_id = payload.new_primary_role_id or existing.primary_role_id
    if next_primary_location_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Primary location is required")

    _assert_user_references(
        engine,
        primary_location_id=next_primary_location_id,
        primary_role_id=next_primary_role_id,
    )

    location_changed = next_primary_location_id != existing.primary_location_id
    role_changed = next_primary_role_id != existing.primary_role_id
    if not location_changed and not role_changed:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User move does not change location or role")

    # Moving is the third path that can strip the admin role — guard it like
    # PATCH and deactivate so no endpoint can demote the last active admin.
    if (
        role_changed
        and existing.primary_role_code == "admin"
        and count_active_admins(engine, user_id) <= 1
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot change the role of the last active admin",
        )

    _assert_transfer_target(engine, user_id, payload.transfer_to_user_id, existing.primary_location_id)

    active_requisition_count = count_user_active_requisitions(engine, user_id)
    active_assignment_count = count_user_active_assignments(engine, user_id)
    active_candidate_owner_count = count_user_active_candidate_ownership(engine, user_id)
    active_pipeline_owner_count = count_user_active_pipeline_ownership(engine, user_id)
    review_required = any(
        count > 0
        for count in (
            active_requisition_count,
            active_assignment_count,
            active_candidate_owner_count,
            active_pipeline_owner_count,
        )
    )

    if review_required and not payload.review_confirmed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User move requires active-work review confirmation",
        )
    if location_changed and review_required and payload.transfer_to_user_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Transfer user is required when moving location with active work",
        )

    updated = transfer_active_user_work_and_move(
        engine,
        user_id=user_id,
        transfer_to_user_id=payload.transfer_to_user_id,
        new_primary_location_id=next_primary_location_id,
        new_primary_role_id=next_primary_role_id,
    )
    try:
        create_notification_service(
            engine,
            NotificationCreate(
                location_id=next_primary_location_id,
                user_id=user_id,
                event_type="user_moved",
                source_type="user",
                source_id=user_id,
                title="Your role or branch was updated",
                message=(
                    "Your role or branch was updated and your active work was transferred. "
                    "Review your new assignment so nothing is left behind."
                ),
                priority="normal",
                action_url=None,
            ),
        )
    except Exception:
        pass
    actor_user_id = payload.changed_by_user_id or (auth_context.user.id if auth_context else None)
    if actor_user_id is not None:
        insert_audit_log(
            engine,
            actor_user_id=actor_user_id,
            location_id=existing.primary_location_id,
            entity_type="user",
            entity_id=user_id,
            action_type="moved_with_transfer_review",
            old_values={
                "primary_location_id": existing.primary_location_id,
                "primary_role_id": existing.primary_role_id,
            },
            new_values={
                "primary_location_id": next_primary_location_id,
                "primary_role_id": next_primary_role_id,
                "transfer_to_user_id": payload.transfer_to_user_id,
                "reason": payload.reason,
                "review_confirmed": payload.review_confirmed,
                "active_requisition_count": active_requisition_count,
                "active_assignment_count": active_assignment_count,
                "active_candidate_owner_count": active_candidate_owner_count,
                "active_pipeline_owner_count": active_pipeline_owner_count,
            },
        )

    return UserMoveResponse(
        user_id=user_id,
        previous_primary_location_id=existing.primary_location_id,
        new_primary_location_id=updated.primary_location_id,
        previous_primary_role_id=existing.primary_role_id,
        new_primary_role_id=updated.primary_role_id,
        transfer_to_user_id=payload.transfer_to_user_id,
        review_required=review_required,
        active_requisition_count=active_requisition_count,
        active_assignment_count=active_assignment_count,
        active_candidate_owner_count=active_candidate_owner_count,
        active_pipeline_owner_count=active_pipeline_owner_count,
        reason=payload.reason,
    )
