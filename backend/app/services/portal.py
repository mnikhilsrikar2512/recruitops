from datetime import date

from fastapi import HTTPException, status
from sqlalchemy import Engine

from app.repositories import portal as portal_repo
from app.schemas.pagination import PaginationMeta
from app.schemas.portal import (
    PortalAccountCreate,
    PortalWeeklyBucket,
    PortalWeeklyUsageEntry,
    PortalAccountListFilters,
    PortalAccountListResponse,
    PortalAccountResponse,
    PortalAccountUpdate,
    PortalAvailabilityFilters,
    PortalAvailabilityResponse,
    PortalSlotCreate,
    PortalSlotListFilters,
    PortalSlotListResponse,
    PortalSlotResponse,
    PortalSlotUpdate,
    PortalWeeklyUsageResponse,
)


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="usage_date must be an ISO date (YYYY-MM-DD)",
        ) from exc


def list_portal_accounts_service(
    engine: Engine, filters: PortalAccountListFilters
) -> PortalAccountListResponse:
    items, total = portal_repo.list_portal_accounts(engine, filters)
    return PortalAccountListResponse(
        items=[PortalAccountResponse.model_validate(item) for item in items],
        meta=PaginationMeta(page=filters.page, page_size=filters.page_size, total=total),
    )


def get_portal_account_service(engine: Engine, portal_account_id: int) -> PortalAccountResponse:
    record = portal_repo.find_portal_account_by_id(engine, portal_account_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portal account was not found",
        )
    return PortalAccountResponse.model_validate(record)


def create_portal_account_service(
    engine: Engine, payload: PortalAccountCreate, actor_user_id: int | None
) -> PortalAccountResponse:
    if not portal_repo.branch_exists(engine, payload.branch_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Branch was not found",
        )
    if payload.owned_by_user_id and not portal_repo.user_exists(engine, payload.owned_by_user_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Owning user was not found",
        )
    record = portal_repo.create_portal_account(engine, payload, actor_user_id)
    return PortalAccountResponse.model_validate(record)


def update_portal_account_service(
    engine: Engine, portal_account_id: int, payload: PortalAccountUpdate
) -> PortalAccountResponse:
    existing = portal_repo.find_portal_account_by_id(engine, portal_account_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portal account was not found",
        )
    if payload.owned_by_user_id and not portal_repo.user_exists(engine, payload.owned_by_user_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Owning user was not found",
        )
    record = portal_repo.update_portal_account(engine, portal_account_id, payload)
    return PortalAccountResponse.model_validate(record)


def list_portal_slots_service(
    engine: Engine, portal_account_id: int, filters: PortalSlotListFilters
) -> PortalSlotListResponse:
    get_portal_account_service(engine, portal_account_id)  # 404 when account is missing
    items, total = portal_repo.list_portal_slots(engine, portal_account_id, filters)
    return PortalSlotListResponse(
        items=[PortalSlotResponse.model_validate(item) for item in items],
        meta=PaginationMeta(page=filters.page, page_size=filters.page_size, total=total),
    )


def _validate_slot_users(engine: Engine, payload: PortalSlotCreate | PortalSlotUpdate) -> None:
    if payload.assigned_user_id and not portal_repo.user_exists(engine, payload.assigned_user_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assigned user was not found",
        )


def create_portal_slot_service(
    engine: Engine, portal_account_id: int, payload: PortalSlotCreate
) -> PortalSlotResponse:
    account = portal_repo.find_portal_account_by_id(engine, portal_account_id)
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portal account was not found",
        )
    if account.status != "active":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Usage slots can only be booked for active portal accounts",
        )
    _validate_slot_users(engine, payload)

    overlapping = portal_repo.list_portal_slots(
        engine,
        portal_account_id,
        PortalSlotListFilters(usage_date=payload.usage_date, page_size=200),
    )[0]
    for slot in overlapping:
        if slot.id is None or slot.status != "planned":
            continue
        if payload.start_time < slot.end_time and slot.start_time < payload.end_time:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Time window overlaps an existing planned slot "
                    f"({slot.start_time}-{slot.end_time})"
                ),
            )

    record = portal_repo.create_portal_slot(engine, portal_account_id, payload)
    return PortalSlotResponse.model_validate(record)


def update_portal_slot_service(
    engine: Engine,
    portal_account_id: int,
    slot_id: int,
    payload: PortalSlotUpdate,
) -> PortalSlotResponse:
    existing = portal_repo.find_portal_slot_by_id(engine, portal_account_id, slot_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portal slot was not found",
        )
    _validate_slot_users(engine, payload)

    effective_start = payload.start_time or existing.start_time
    effective_end = payload.end_time or existing.end_time
    effective_date = payload.usage_date or existing.usage_date
    if effective_end <= effective_start:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="end_time must be after start_time",
        )
    others = [
        slot
        for slot in portal_repo.list_portal_slots(
            engine,
            portal_account_id,
            PortalSlotListFilters(usage_date=effective_date, page_size=200),
        )[0]
        if slot.id != slot_id
    ]
    for slot in others:
        if slot.status != "planned":
            continue
        if effective_start < slot.end_time and slot.start_time < effective_end:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Time window overlaps an existing planned slot "
                    f"({slot.start_time}-{slot.end_time})"
                ),
            )

    updated = portal_repo.update_portal_slot(
        engine, portal_account_id, slot_id, payload
    )
    return PortalSlotResponse.model_validate(updated)


def delete_portal_slot_service(engine: Engine, portal_account_id: int, slot_id: int) -> None:
    existing = portal_repo.find_portal_slot_by_id(engine, portal_account_id, slot_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portal slot was not found",
        )
    portal_repo.delete_portal_slot(engine, portal_account_id, slot_id)


def portal_availability_service(
    engine: Engine,
    platform: str | None,
    branch_id: int | None,
    usage_date: str | None,
) -> PortalAvailabilityResponse:
    filters = PortalAvailabilityFilters(
        platform=platform,
        branch_id=branch_id,
        usage_date=_parse_date(usage_date),
    )
    return PortalAvailabilityResponse(
        items=portal_repo.list_portal_availability(engine, filters)
    )


def portal_usage_summary_service(
    engine: Engine, weeks_back: int = 6
) -> PortalWeeklyUsageResponse:
    """Booked hours per platform per week for the analytics dashboard report."""
    rows = portal_repo.summarize_portal_usage_by_week(engine, weeks_back)

    week_starts: list[date] = []
    by_platform: dict[str, dict[date, int]] = {}
    for row in rows:
        platform = row["platform_name"]
        week_start = row["week_start"]
        if week_start not in week_starts:
            week_starts.append(week_start)
        by_platform.setdefault(platform, {})[week_start] = (
            by_platform.get(platform, {}).get(week_start, 0) + row["booked_minutes"]
        )

    week_starts.sort()
    platforms = sorted(by_platform)
    entries = []
    for platform in platforms:
        buckets = [
            PortalWeeklyBucket(
                week_start=week_start,
                booked_hours=round(by_platform[platform].get(week_start, 0) / 60.0, 1),
            )
            for week_start in week_starts
        ]
        entries.append(
            PortalWeeklyUsageEntry(
                platform_name=platform,
                weeks=buckets,
                total_hours=round(
                    sum(bucket.booked_hours for bucket in buckets), 1
                ),
            )
        )

    return PortalWeeklyUsageResponse(weeks=week_starts, platforms=entries)
