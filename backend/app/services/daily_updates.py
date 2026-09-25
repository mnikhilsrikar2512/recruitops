from fastapi import HTTPException, status
from sqlalchemy import Engine

from app.repositories.daily_updates import (
    count_daily_updates_for_user_requisition_date,
    create_daily_update,
    find_daily_update_by_id,
    has_user_requisition_link,
    list_daily_updates,
)
from app.repositories.requisitions import find_requisition_by_id
from app.repositories.users import find_user_by_id
from app.schemas.daily_update import (
    DailyUpdateCreate,
    DailyUpdateListFilters,
    DailyUpdateListResponse,
    DailyUpdateResponse,
)
from app.schemas.notification import NotificationCreate
from app.schemas.pagination import PaginationMeta
from app.services.notifications import create_notification_service


def list_daily_updates_service(engine: Engine, filters: DailyUpdateListFilters) -> DailyUpdateListResponse:
    items, total = list_daily_updates(engine, filters)
    return DailyUpdateListResponse(
        items=[DailyUpdateResponse.model_validate(item) for item in items],
        meta=PaginationMeta(page=filters.page, page_size=filters.page_size, total=total),
    )


def create_daily_update_service(engine: Engine, payload: DailyUpdateCreate) -> DailyUpdateResponse:
    user = find_user_by_id(engine, payload.submitted_by_user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submitted by user was not found")
    requisition = find_requisition_by_id(engine, payload.requisition_id)
    if not requisition:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Requisition was not found")
    is_admin = str(getattr(user, "primary_role_code", "") or "").lower() == "admin"
    same_location = user.primary_location_id == requisition.location_id
    if not is_admin and user.primary_location_id is not None and not same_location:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Submitted by user must belong to the same location as the requisition",
        )
    owns_requisition = has_user_requisition_link(
        engine,
        user_id=payload.submitted_by_user_id,
        requisition_id=payload.requisition_id,
    )
    if not owns_requisition and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Submitted by user must be linked to the requisition",
        )
    if count_daily_updates_for_user_requisition_date(
        engine,
        submitted_by_user_id=payload.submitted_by_user_id,
        requisition_id=payload.requisition_id,
        update_date=payload.update_date,
    ) > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Daily update already exists for this requisition, user, and date",
        )
    created = create_daily_update(engine, requisition.location_id, payload)
    requisition_owner = getattr(requisition, "primary_owner_user_id", None)
    submitter_id = getattr(payload, "submitted_by_user_id", None)
    if requisition_owner and requisition_owner != submitter_id:
        try:
            create_notification_service(
                engine,
                NotificationCreate(
                    location_id=requisition.location_id,
                    user_id=requisition.primary_owner_user_id,
                    event_type="daily_update_submitted",
                    source_type="daily_update",
                    source_id=created.id,
                    title="A daily update was submitted",
                    message=(
                        f"A daily update was submitted for {requisition.title}. "
                        "Read it and follow up on blockers."
                    ),
                    priority="low",
                    action_url=f"/daily-updates/{created.id}",
                ),
            )
        except Exception:
            pass
    return DailyUpdateResponse.model_validate(created)


def get_daily_update_detail_service(engine: Engine, daily_update_id: int) -> DailyUpdateResponse:
    daily_update = find_daily_update_by_id(engine, daily_update_id)
    if not daily_update:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Daily update was not found")
    return DailyUpdateResponse.model_validate(daily_update)
